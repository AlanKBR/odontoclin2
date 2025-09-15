from __future__ import annotations

from logging.config import fileConfig
from typing import Any

from alembic import context as _context  # type: ignore[attr-defined]

# Expose name 'context' with flexible typing for attribute access used by Alembic
context: Any = _context

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_app():
    from app import create_app

    return create_app()


app = get_app()


def _get_bind_name() -> str | None:
    """Return the configured target bind name, if any.

    We read a custom option `target_bind` from alembic.ini under the [alembic]
    section. When set, migrations run against that SQLAlchemy bind instead of
    the default database URI. This preserves separate DB files per module.
    """
    try:
        return config.get_main_option("target_bind")
    except Exception:
        return None


def run_migrations_offline() -> None:
    with app.app_context():
        bind_name = _get_bind_name()
        if bind_name:
            # Use the configured bind URL (separate DB file)
            url = app.config["SQLALCHEMY_BINDS"][bind_name]
        else:
            url = app.config["SQLALCHEMY_DATABASE_URI"]

        context.configure(
            url=url,
            target_metadata=None,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online() -> None:
    from app import db as _db

    with app.app_context():
        bind_name = _get_bind_name()
        if bind_name:
            connectable = _db.get_engine(app=app, bind=bind_name)
        else:
            connectable = _db.get_engine(app=app)

        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=None)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
