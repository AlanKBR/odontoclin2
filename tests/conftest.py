import os
import sys
import tempfile

import pytest

# Ensure project root (parent of tests) is on sys.path before importing app
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app, db  # noqa: E402


@pytest.fixture()
def app():
    # Configuração isolada usando banco temporário para principal e binds
    tmpdir = tempfile.TemporaryDirectory()
    instance = tmpdir.name

    class TestConfig:
        TESTING = True
        SECRET_KEY = "test"
        TEST_SKIP_AUTH = False
        DEBUG_LOGIN_BYPASS = True
        WTF_CSRF_ENABLED = False
        ENFORCE_PASSWORD_POLICY = False  # desativa política em testes
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(instance, "main.db")
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SQLALCHEMY_BINDS = {
            "calendario": ("sqlite:///" + os.path.join(instance, "calendario.db")),
            "pacientes": ("sqlite:///" + os.path.join(instance, "pacientes.db")),
            "users": "sqlite:///" + os.path.join(instance, "users.db"),
            "tratamentos": ("sqlite:///" + os.path.join(instance, "tratamentos.db")),
            "receitas": ("sqlite:///" + os.path.join(instance, "receitas.db")),
        }

    flask_app = create_app(TestConfig)
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        # Importa apenas models; evita importar módulos de rotas/blueprints
        # para não reexecutar decorators após o registro do blueprint.
        from app.agenda.models import CalendarEvent, Holiday  # noqa
        from app.catalogo import models as catalogo_models  # noqa
        from app.core import models as core_models  # noqa: F401 ensure clinica
        from app.documentos import models as documentos_models  # noqa: F401
        from app.pacientes import models as pacientes_models  # noqa
        from app.receitas import models as receitas_models  # noqa: F401

        if not flask_app.config.get("TEST_SKIP_AUTH"):
            from app.auth import models as auth_models  # noqa
        db.create_all()
    yield flask_app
    # Libera conexões para evitar lock em Windows ao remover diretório
    with flask_app.app_context():
        db.session.remove()
        # Substitui get_engine() deprecated por engine/engines
        try:
            db.engine.dispose()
        except Exception:  # pragma: no cover - best effort
            pass
        for bind_engine in db.engines.values():  # inclui binds
            try:
                bind_engine.dispose()
            except Exception:  # pragma: no cover
                pass
    tmpdir.cleanup()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
