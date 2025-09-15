import os
import secrets  # Add secrets
from datetime import date, datetime, timezone  # Add timezone
from typing import Union  # Add Union for Python < 3.10 compatibility if needed

from flask import Flask, render_template
from markupsafe import Markup, escape

from app.models.user import User

# Import AI Assistant blueprint but with lazy route handling
from app.routes.ai_assistant import ai_assistant_bp
from app.routes.atestados import atestados_bp  # Adicionando o novo blueprint de atestados

# Import blueprints and models at the top level
from app.routes.auth import auth
from app.routes.cro import cro_bp  # Adicionando o novo blueprint de CRO
from app.routes.documentos import documentos_bp  # Adicionando o novo blueprint de documentos
from app.routes.main import main
from app.routes.pacientes import pacientes
from app.routes.receitas import receitas  # Adicionando o novo blueprint de receitas
from app.routes.tratamentos import tratamentos
from app.routes.users import users

# Import extensions from the new extensions.py file
from .extensions import db, login_manager, mobility
from .multidb import multidb


def create_app() -> Flask:
    app = Flask(__name__)

    # Enable Jinja2 'do' extension
    app.jinja_env.add_extension("jinja2.ext.do")

    # Configuração do banco de dados
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "chave-secreta-temporaria")

    # Diretório instance
    instance_path = os.path.abspath(os.path.join(app.root_path, "..", "instance"))

    # Configuração dos bancos de dados separados
    # Use instance folder for the main app.db to keep all DBs under instance
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(instance_path, 'app.db')}"
    )
    app.config["USERS_DATABASE_URI"] = os.environ.get(
        "USERS_DATABASE_URI", f"sqlite:///{os.path.join(instance_path, 'users.db')}"
    )
    app.config["PACIENTES_DATABASE_URI"] = os.environ.get(
        "PACIENTES_DATABASE_URI",
        f"sqlite:///{os.path.join(instance_path, 'pacientes.db')}",
    )
    app.config["TRATAMENTOS_DATABASE_URI"] = os.environ.get(
        "TRATAMENTOS_DATABASE_URI",
        f"sqlite:///{os.path.join(instance_path, 'tratamentos.db')}",
    )
    app.config["RECEITAS_DATABASE_URI"] = os.environ.get(
        "RECEITAS_DATABASE_URI",
        f"sqlite:///{os.path.join(instance_path, 'receitas.db')}",
    )
    app.config["CALENDARIO_DATABASE_URI"] = os.environ.get(
        "CALENDARIO_DATABASE_URI",
        f"sqlite:///{os.path.join(instance_path, 'calendario.db')}",
    )

    # Inicializa extensões
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_BINDS"] = {
        "users": app.config["USERS_DATABASE_URI"],
        "pacientes": app.config["PACIENTES_DATABASE_URI"],
        "tratamentos": app.config["TRATAMENTOS_DATABASE_URI"],
        "receitas": app.config["RECEITAS_DATABASE_URI"],
        "calendario": app.config["CALENDARIO_DATABASE_URI"],
    }

    # Disable CSRF protection completely
    app.config["WTF_CSRF_ENABLED"] = False

    # Inicializa Flask-Mobility para detecção de dispositivos móveis
    mobility.init_app(app)

    # Inicializa os bancos de dados
    db.init_app(app)  # Initialize the main db instance first

    # Inicializa sistema de múltiplos bancos de dados, passing the main db instance
    multidb.init_app(app, db_instance=db)  # Pass the db instance from extensions

    # Update the placeholder variables in extensions.py
    from . import extensions

    extensions.users_db = multidb.get_session("users")
    extensions.pacientes_db = multidb.get_session("pacientes")
    extensions.tratamentos_db = multidb.get_session("tratamentos")
    extensions.receitas_db = multidb.get_session("receitas")

    # Configuração do login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # type: ignore
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "info"

    # Registra os blueprints
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(main, url_prefix="/")
    app.register_blueprint(pacientes, url_prefix="/pacientes")
    app.register_blueprint(tratamentos, url_prefix="/tratamentos")
    app.register_blueprint(users, url_prefix="/users")
    app.register_blueprint(receitas, url_prefix="/receitas")  # Registro do blueprint de receitas
    app.register_blueprint(cro_bp, url_prefix="/cro")  # Registro do blueprint de CRO
    app.register_blueprint(
        atestados_bp, url_prefix="/atestados"
    )  # Registro do blueprint de atestados
    app.register_blueprint(
        documentos_bp, url_prefix="/documentos"
    )  # Registro do blueprint de documentos
    app.register_blueprint(
        ai_assistant_bp, url_prefix="/ai"
    )  # Registro do blueprint de IA com lazy loading

    # Integra o módulo de Agenda (calendário) como um blueprint em /agenda
    # Preferimos registrar o blueprint diretamente; se falhar, tentamos via init_agenda.
    try:
        from agenda.db import db as agenda_db  # type: ignore
        from agenda.routes import bp as agenda_bp  # type: ignore

        agenda_db.init_app(app)
        app.register_blueprint(agenda_bp, url_prefix="/agenda")
        with app.app_context():
            try:
                # Create default-bind tables (e.g., app_settings in app.db)
                # Calendar-related tables are managed via one-off migration script and not on startup
                agenda_db.create_all()
            except Exception:
                pass
    except Exception:
        try:
            from agenda import init_agenda  # type: ignore

            init_agenda(app, url_prefix="/agenda", auto_create_db=True)
        except Exception as ex:
            try:
                app.logger.exception("Falha ao inicializar Agenda: %s", ex)
            except Exception:
                print("Falha ao inicializar Agenda:", ex)

    # Custom Jinja filter for date formatting
    def format_date_filter(value: Union[datetime, date], format: str = "%d/%m/%Y") -> str:
        if value and isinstance(value, (datetime, date)):
            return value.strftime(format)
        return str(value)

    app.jinja_env.filters["date"] = format_date_filter

    # Custom Jinja filter to convert newlines to <br>
    def nl2br(value: str) -> str:
        if not value:
            return ""
        return Markup(escape(value).replace("\n", "<br>"))

    app.jinja_env.filters["nl2br"] = nl2br

    @app.context_processor
    def inject_now() -> dict[str, datetime]:
        """
        Injects the current UTC datetime into Jinja2 templates.
        """
        return {"now": datetime.now(timezone.utc)}

    @app.context_processor
    def inject_csp_nonce():
        """
        Provides a Content Security Policy (CSP) nonce for Jinja2 templates.
        """
        nonce = secrets.token_hex(16)
        return {"csp_nonce": lambda: nonce}

    @app.context_processor
    def inject_mobility() -> dict:
        """
        Injects mobility information into templates.
        """
        from flask import request

        return {"is_mobile": getattr(request, "MOBILE", False)}

    @app.context_processor
    def inject_ai_status() -> dict:
        """
        Injects AI availability status into templates.
        Checks if AI is enabled and working without heavy imports.
        """
        try:
            import os

            config_path = os.path.join("config", "ai_settings.json")
            if os.path.exists(config_path):
                import json

                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                ai_enabled = settings.get("ai_enabled", False)
                return {"ai_available": ai_enabled, "ai_can_load": ai_enabled}
            return {"ai_available": False, "ai_can_load": False}
        except Exception:
            return {"ai_available": False, "ai_can_load": False}

    @app.context_processor
    def inject_endpoint_utils() -> dict:
        """Expose a helper to check if a Flask endpoint exists."""

        def endpoint_exists(name: str) -> bool:
            try:
                return name in app.view_functions
            except Exception:
                return False

        return {"endpoint_exists": endpoint_exists}

    @login_manager.user_loader
    def load_user(user_id: str) -> Union[User, None]:  # Assuming User model or None
        return User.query.get(int(user_id))

    # Adiciona função personalizada ao contexto Jinja
    app.jinja_env.globals.update(csp_nonce=lambda: Markup(""))

    # Registra função de erro 404
    @app.errorhandler(404)
    def page_not_found(e: Exception) -> tuple[str, int]:  # Or specific exception type
        return render_template("404.html"), 404

    # Registra função de erro 500
    @app.errorhandler(500)
    def internal_server_error(
        e: Exception,
    ) -> tuple[str, int]:  # Or specific exception type
        return render_template("500.html"), 500

    @app.template_filter("currency")
    def _jinja2_filter_currency(
        value: Union[float, int, None],
    ) -> str:  # Assuming value is numeric or None
        if value is None:
            return "R$ 0,00"
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Adiciona filtro Jinja para verificar existência de arquivo
    def file_exists_filter(path):
        import os

        base = app.root_path
        abs_path = os.path.join(base, path) if not os.path.isabs(path) else path
        return os.path.exists(abs_path)

    app.jinja_env.filters["file_exists"] = file_exists_filter

    # Context processor para disponibilizar informações da clínica em todos os templates
    @app.context_processor
    def inject_clinica_info():
        from app.models.clinica import Clinica

        try:
            clinica = Clinica.get_instance()
            return {"clinica_global": clinica}
        except Exception:
            # Se houver erro ao acessar o banco, retorna dados padrão
            return {"clinica_global": None}

    return app
