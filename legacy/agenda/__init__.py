import os

from flask import Flask

from .db import db as agenda_db


def init_agenda(
    app: Flask,
    *,
    database_uri: str | None = None,
    auto_create_db: bool = True,
    url_prefix: str = "",
) -> None:
    """Initialize and register the Agenda blueprint on an existing app.

    Parameters:
    - app: Flask application instance.
    - database_uri: optional SQLAlchemy URI. If omitted, uses
      sqlite:///<app.root_path>/instance/calendario.db
    - auto_create_db: whether to create tables on init (default True).
    - url_prefix: optional URL prefix for the blueprint (default '').
    """

    # Prefer using the host app's SQLAlchemy instance if already configured
    local_db = agenda_db
    try:  # Try to import the main app's db instance
        from app.extensions import db as main_db  # type: ignore

        # If the host app already initialized Flask-SQLAlchemy, reuse it
        if hasattr(app, "extensions") and isinstance(getattr(app, "extensions", {}), dict):
            if "sqlalchemy" in app.extensions:
                local_db = main_db
                # Rebind our module-level 'db' to the main instance for model mappings
                try:
                    import agenda.db as _agenda_db_mod  # type: ignore

                    _agenda_db_mod.db = main_db
                except Exception:
                    pass
    except Exception:
        # Fallback: keep using agenda's own db instance
        pass

    # Configure SQLAlchemy only if we're using our own instance (not the host's)
    if local_db is agenda_db:
        if not database_uri:
            # Use the application's instance_path (outside the package by default)
            os.makedirs(app.instance_path, exist_ok=True)
            db_path = os.path.join(app.instance_path, "calendario.db")
            database_uri = f"sqlite:///{db_path}"
        app.config.setdefault("SQLALCHEMY_DATABASE_URI", database_uri)
        app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
        local_db.init_app(app)

    # Import blueprint and models only after binding the correct db instance
    from .routes import bp as bp_agenda  # local import to avoid cycles, after db binding

    # Register blueprint
    app.register_blueprint(bp_agenda, url_prefix=url_prefix)

    # Optionally create tables
    if auto_create_db:
        # One-time migration: if there are DBs under old agenda/instance,
        # copy them into app.instance_path (non-destructive).
        try:
            import shutil

            old_instance = os.path.join(os.path.dirname(__file__), "instance")
            for fname in ("calendario.db", "pacientes.db", "users.db"):
                old_f = os.path.join(old_instance, fname)
                new_f = os.path.join(app.instance_path, fname)
                if os.path.exists(old_f) and not os.path.exists(new_f):
                    os.makedirs(os.path.dirname(new_f), exist_ok=True)
                    shutil.copy2(old_f, new_f)
        except Exception:
            # Best-effort only
            pass
        with app.app_context():
            try:
                local_db.create_all()
            except Exception:
                # Tables may already exist or be managed externally
                pass


def create_app(
    *,
    config: dict | None = None,
    database_uri: str | None = None,
    url_prefix: str = "",
) -> Flask:
    """App factory that returns a standalone Flask app with Agenda.

    Accepts optional config and database_uri to ease reuse.
    """
    # Default instance folder placed at repo/app root: ../instance
    default_instance = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "instance")
    )
    app = Flask(
        __name__,
        instance_path=default_instance,
        template_folder="templates",
        static_folder="static",
    )

    if config:
        app.config.update(config)

    init_agenda(
        app,
        database_uri=database_uri,
        auto_create_db=True,
        url_prefix=url_prefix,
    )
    return app


# Optional public exports for convenience in host apps
try:  # pragma: no cover - convenience only
    from .routes import bp as agenda_blueprint  # noqa: WPS433
except Exception:  # pragma: no cover
    agenda_blueprint = None  # type: ignore

__all__ = [
    "init_agenda",
    "create_app",
    "agenda_blueprint",
    "db",
]
