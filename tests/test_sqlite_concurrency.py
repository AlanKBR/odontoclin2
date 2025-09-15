import sqlite3
import threading
import time

from app import db
from app.pacientes.models import Paciente
from app.utils_db import commit_with_retry, transactional


def _get_sqlite_path(uri: str) -> str:
    assert uri.startswith("sqlite:///"), "Only sqlite URIs are supported in this test"
    return uri.replace("sqlite:///", "")


def test_pragmas_applied_on_all_binds(app):
    """Verify PRAGMAs (WAL, foreign_keys, busy_timeout) are active on all engines.

    We only check SQLite engines. The global connect hook should set PRAGMAs
    for the default engine and all binds.
    """
    with app.app_context():
        engines = {"default": db.engine, **db.engines}
        for name, engine in engines.items():
            if engine.dialect.name != "sqlite":
                continue
            with engine.connect() as conn:
                journal_mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
                foreign_keys = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
                busy_timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
                assert str(journal_mode).lower() == "wal", f"{name}: journal_mode should be WAL"
                assert int(foreign_keys or 0) == 1, f"{name}: foreign_keys should be ON"
                assert int(busy_timeout or 0) >= 1000, f"{name}: busy_timeout should be set (>=1s)"


def test_commit_with_retry_handles_busy(app):
    """Simulate a transient lock and ensure commit_with_retry succeeds.

    We open a raw sqlite3 connection to the pacientes.db file and begin a
    transaction holding a write lock briefly, then attempt a SQLAlchemy commit
    in parallel. The busy_timeout + retry should allow it to complete.
    """
    with app.app_context():
        pacientes_uri = app.config["SQLALCHEMY_BINDS"]["pacientes"]
        pacientes_path = _get_sqlite_path(pacientes_uri)

        # Ensure table exists
        db.create_all()

        # Thread 1: hold a write transaction for a short time
        def hold_write_lock():
            con = sqlite3.connect(pacientes_path)
            cur = con.cursor()
            try:
                cur.execute("BEGIN IMMEDIATE")  # acquire write lock
                # Touch a temp table to ensure write lock is established
                cur.execute("CREATE TABLE IF NOT EXISTS _lock_test(id INTEGER)")
                time.sleep(0.8)  # hold the lock for < busy_timeout (5s)
                con.commit()
            finally:
                con.close()

        t = threading.Thread(target=hold_write_lock)
        t.start()
        time.sleep(0.1)  # give lock thread a head start

        # Thread 2 (main): attempt a commit during the lock window
        p = Paciente()
        p.nome = "Teste Busy"
        db.session.add(p)
        # Should wait and succeed without raising due to our retry helper
        commit_with_retry(max_retries=5, backoff_seconds=0.1)

        # Validate persisted
        saved = db.session.get(Paciente, p.id)
        assert saved is not None and saved.nome == "Teste Busy"

        t.join()


def test_transactional_context_manager(app):
    with app.app_context():
        name = f"Paciente {time.time()}"
        with transactional():
            p = Paciente()
            p.nome = name
            db.session.add(p)
        got = Paciente.query.filter_by(nome=name).first()
        assert got is not None


def test_automatic_session_retry_without_helper(app):
    """Ensure the Session subclass retries automatically even without helper.

    This simulates a brief write lock and attempts a normal db.session.commit().
    """
    with app.app_context():
        pacientes_uri = app.config["SQLALCHEMY_BINDS"]["pacientes"]
        pacientes_path = _get_sqlite_path(pacientes_uri)

        def hold_write_lock():
            con = sqlite3.connect(pacientes_path)
            cur = con.cursor()
            try:
                cur.execute("BEGIN IMMEDIATE")
                cur.execute("CREATE TABLE IF NOT EXISTS _lock_test2(id INTEGER)")
                time.sleep(0.6)
                con.commit()
            finally:
                con.close()

        t = threading.Thread(target=hold_write_lock)
        t.start()
        time.sleep(0.1)

        p = Paciente()
        p.nome = "AutoRetry"
        db.session.add(p)
        # No helper here: direct commit should succeed due to RetrySession
        db.session.commit()

        saved = db.session.get(Paciente, p.id)
        assert saved is not None and saved.nome == "AutoRetry"

        t.join()
