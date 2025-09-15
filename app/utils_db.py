import time
import logging
from contextlib import contextmanager

from flask import abort
from sqlalchemy.exc import OperationalError

from . import db


def get_or_404(model, ident):
    """Lightweight replacement for Model.query.get_or_404 using Session.get.

    Avoids SQLAlchemy 2.x LegacyAPIWarning emitted by Query.get().
    """
    obj = db.session.get(model, ident)
    if obj is None:
        abort(404)
    return obj


def _is_sqlite_busy(error: BaseException) -> bool:
    # Detects SQLITE_BUSY or SQLITE_LOCKED conditions surfaced via SQLAlchemy
    msg = str(error).lower()
    return ("database is locked" in msg) or ("database is busy" in msg) or ("sqlite_busy" in msg)


def commit_with_retry(max_retries: int = 5, backoff_seconds: float = 0.1) -> None:
    """Commit current session with retry on transient SQLite lock.

    Centralizes a simple policy: when a concurrent writer holds the lock, we
    wait a bit and retry the commit. Combined with PRAGMA busy_timeout, this
    further reduces spurious failures under light contention.
    """
    attempt = 0
    logger = logging.getLogger("db.retry")
    while True:
        try:
            db.session.commit()
            return
        except OperationalError as exc:  # pragma: no cover - relies on runtime contention
            if attempt < max_retries and _is_sqlite_busy(exc):
                attempt += 1
                time.sleep(backoff_seconds * (2 ** (attempt - 1)))
                continue
            logger.error("SQLite commit failed after %s retries: %s", attempt, exc)
            raise


@contextmanager
def transactional(max_retries: int = 3, backoff_seconds: float = 0.2):
    """Context manager for a commit-with-retry transaction.

    Usage:
        with transactional():
            # make changes on db.session
            ...
    """
    try:
        yield
        commit_with_retry(max_retries=max_retries, backoff_seconds=backoff_seconds)
    except Exception:
        db.session.rollback()
        raise
