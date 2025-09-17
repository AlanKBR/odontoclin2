import os
import sqlite3
import time
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from flask_sqlalchemy.session import Session as FsaSession

"""Aplicação principal e fábrica Flask.

Blueprints são importados dentro de create_app para evitar ciclos de
importação (especialmente com auth durante testes).
"""


# Extensões globais (inicializadas no create_app)
#
# Session com retry automático em commits quando SQLite sinaliza bloqueio
class RetrySession(FsaSession):  # pragma: no cover - validado via testes de integração
    _retry_max = 5
    _retry_backoff = 0.1

    @staticmethod
    def _is_sqlite_busy(error: BaseException) -> bool:
        msg = str(error).lower()
        return (
            "database is locked" in msg
            or "database is busy" in msg
            or "sqlite_busy" in msg
            or "database table is locked" in msg
        )

    def commit(self) -> None:  # type: ignore[override]
        attempts = 0
        logger = logging.getLogger("db.retry")
        while True:
            try:
                super().commit()
                return
            except OperationalError as exc:
                if attempts < self._retry_max and self._is_sqlite_busy(exc):
                    attempts += 1
                    # Após erro a transação pode ficar inválida: rollback antes de tentar novamente
                    try:
                        super().rollback()
                    except Exception:
                        pass
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("SQLite busy detected; retry %s/%s", attempts, self._retry_max)
                    time.sleep(self._retry_backoff * (2 ** (attempts - 1)))
                    continue
                # Exhausted retries or non-busy error
                logger.error("SQLite commit failed after %s retries: %s", attempts, exc)
                raise


db = SQLAlchemy(session_options={"class_": RetrySession})
csrf = CSRFProtect()


# Centraliza PRAGMAs do SQLite para todas as conexões criadas pelo SQLAlchemy.
# Isso habilita WAL (melhor concorrência de leitura), ativa foreign_keys,
# e configura busy_timeout para que, durante escrita concorrente, a outra
# transação aguarde alguns segundos antes de lançar erro "database is locked".
@event.listens_for(Engine, "connect")
def _sqlite_pragmas_on_connect(dbapi_connection, connection_record):  # pragma: no cover - infra
    if isinstance(dbapi_connection, sqlite3.Connection):
        cur = dbapi_connection.cursor()
        try:
            # WAL melhora concorrência de leitura; mantém compatibilidade com backups via API
            cur.execute("PRAGMA journal_mode=WAL")
        except Exception:
            # Algumas conexões 'ATTACH' podem não aceitar journal_mode aqui; ignorar com segurança
            pass
        # Ativa integridade referencial e define timeout de espera ao encontrar bloqueios
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=1000")  # 1s de espera por bloqueio
        # Reduz fsyncs mantendo durabilidade boa no contexto de app (ajuste conforme necessidade)
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)

    # Config padrão base
    app.config.from_object("config.Config")

    # Override opcional
    if config_object:
        app.config.from_object(config_object)

    # Garante existência da pasta instance
    os.makedirs(app.instance_path, exist_ok=True)

    # Inicializa extensões
    db.init_app(app)
    csrf.init_app(app)

    # Ampliar busca de templates: além de templates padrão, inclui raiz do pacote 'app'
    # para permitir paths como 'core/base.html' e 'modulo/arquivo.html'.
    try:
        from jinja2 import ChoiceLoader, FileSystemLoader

        existing_loader = app.jinja_env.loader  # mantém loaders padrão/blueprints
        loaders: list[object] = []
        if existing_loader is not None:
            loaders.append(existing_loader)
        loaders.extend(
            [
                FileSystemLoader(app.root_path),  # ex: app/core/base.html
                FileSystemLoader(os.path.join(app.root_path, "templates")),
            ]
        )
        app.jinja_env.loader = ChoiceLoader(loaders)  # type: ignore[assignment]
    except Exception:  # pragma: no cover - ambiente sem jinja2 improvável
        pass

    # Segurança básica de sessão (pode ser ajustada em produção via env)
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    # Em produção, HTTPS recomendado
    if app.config.get("ENV") == "production":  # pragma: no cover
        app.config.setdefault("SESSION_COOKIE_SECURE", True)

    # Importa e registra blueprints tardiamente
    from .agenda.agenda import agenda_bp  # noqa: WPS433
    from .ai_assistant.ai_assistant import ai_assistant_bp  # noqa: WPS433
    from .atestados.atestados import atestados_bp  # noqa: WPS433
    from .catalogo.catalogo import catalogo_bp  # noqa: WPS433
    from .core.core import core_bp  # noqa: WPS433
    from .cro.cro import cro_bp  # noqa: WPS433
    from .calculadora_anestesico.calculadora_anestesico import (
        calc_anestesico_bp,
    )  # noqa: WPS433
    from .documentos.documentos import documentos_bp  # noqa: WPS433
    from .main.main import main_bp  # noqa: WPS433
    from .pacientes.pacientes import pacientes_bp  # noqa: WPS433
    from .receitas.receitas import receitas_bp  # noqa: WPS433
    from .reports.reports import reports_bp  # noqa: WPS433
    from .users.users import users_bp  # noqa: WPS433

    app.register_blueprint(core_bp)
    app.register_blueprint(agenda_bp, url_prefix="/agenda")
    app.register_blueprint(pacientes_bp, url_prefix="/pacientes")

    if not app.config.get("TEST_SKIP_AUTH"):
        from .auth.auth import auth_bp  # noqa: WPS433

        app.register_blueprint(auth_bp, url_prefix="/auth")

    app.register_blueprint(catalogo_bp, url_prefix="/catalogo")
    app.register_blueprint(receitas_bp, url_prefix="/receitas")
    app.register_blueprint(atestados_bp, url_prefix="/atestados")
    app.register_blueprint(documentos_bp, url_prefix="/documentos")
    app.register_blueprint(main_bp, url_prefix="/dashboard")
    app.register_blueprint(cro_bp, url_prefix="/cro")
    app.register_blueprint(calc_anestesico_bp, url_prefix="/calculadora-anestesico")
    app.register_blueprint(ai_assistant_bp, url_prefix="/ai")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(users_bp, url_prefix="/users")

    # Best-effort users schema upgrade (ensure legacy users.db columns)
    try:  # pragma: no cover - infra best-effort
        from .auth.upgrade import ensure_users_schema

        with app.app_context():
            ensure_users_schema()
    except Exception:
        pass

    # Migrações Alembic (opcional) antes de fallback create_all
    if not app.config.get("TESTING") and app.config.get("AUTO_ALEMBIC_UPGRADE"):
        with app.app_context():
            try:  # pragma: no cover - infra best effort
                import importlib  # defer to avoid hard deps in lint

                alembic_command = importlib.import_module("alembic.command")
                alembic_config_mod = importlib.import_module("alembic.config")
                AlembicConfig = getattr(alembic_config_mod, "Config")

                alembic_cfg = AlembicConfig("alembic.ini")
                # Observação: para migrar binds separados use a CLI:
                #   alembic upgrade head -x target_bind=<nome>
                alembic_command.upgrade(alembic_cfg, "head")
            except Exception:
                pass

    # Best-effort compatibility: ensure older DB files have expected columns.
    # Some installations may have an older/smaller schema; try to add missing
    # columns that our code expects to avoid 500s in development. This runs
    # only when not testing and if the DB file exists (safe best-effort).
    try:
        if not app.config.get("TESTING"):
            with app.app_context():
                # Try to use the 'pacientes' bind engine first (Atestado uses that bind)
                try:
                    engine = db.get_engine(app=app, bind="pacientes")
                except Exception:
                    engine = db.get_engine(app=app)

                insp = None
                try:
                    from sqlalchemy import inspect

                    insp = inspect(engine)
                except Exception:
                    insp = None

                if insp is not None and "atestados" in insp.get_table_names():
                    cols = [c.get("name") for c in insp.get_columns("atestados")]
                    # older schema may miss 'paciente' human-friendly name column
                    if "paciente" not in cols:
                        try:
                            with engine.connect() as conn:
                                conn.execute(
                                    text("ALTER TABLE atestados ADD COLUMN paciente VARCHAR(150)")
                                )
                        except Exception:
                            # If alter fails, don't crash app startup; it's best-effort
                            pass
    except Exception:
        pass

    # Em testes mantemos create_all direto (isolado por diretório temp)
    if app.config.get("TESTING"):
        with app.app_context():
            from .catalogo import models as catalogo_models  # noqa
            from .documentos import models as _doc_models  # noqa
            from .pacientes import models as pacientes_models  # noqa
            from .receitas import models as receitas_models  # noqa

            if not app.config.get("TEST_SKIP_AUTH"):
                from .auth import models as auth_models  # noqa
            db.create_all()

    @app.route("/health")
    def health():  # pragma: no cover - endpoint trivial
        return {"status": "ok"}

    return app
