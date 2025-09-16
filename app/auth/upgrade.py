"""Best-effort schema upgrades for the users database (SQLite).

This runs at app startup to add missing columns required by the current User model,
keeping legacy users.db compatible without requiring a full Alembic migration.
"""

from __future__ import annotations

from typing import Set

from sqlalchemy.exc import OperationalError

from .. import db


def ensure_users_schema() -> None:
    """Ensure users table has required columns; create if missing.

    Works only for SQLite; uses simple ALTER TABLE ADD COLUMN statements.
    """
    eng = db.engines.get("users") if hasattr(db, "engines") else None
    engine = eng or db.engine
    try:
        with engine.connect() as conn:
            rows = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
            cols: Set[str] = {row[1] for row in rows}
            if not cols:
                # Table likely absent; create via metadata for the users bind
                db.create_all(bind_key="users")
                rows = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
                cols = {row[1] for row in rows}

            def add_col(name: str, ddl: str) -> None:
                if name not in cols:
                    conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {name} {ddl}")

            # Columns expected by current model
            add_col("cro", "VARCHAR(20)")
            add_col("nome_profissional", "VARCHAR(120)")
            add_col("cargo", "VARCHAR(50) DEFAULT 'dentista'")
            add_col("is_active", "BOOLEAN DEFAULT 1")
            add_col("criado_em", "TIMESTAMP")
            add_col("failed_login_count", "INTEGER DEFAULT 0")
            add_col("locked_until", "TIMESTAMP")
            add_col("last_password_change", "TIMESTAMP")

            # --- Ensure auxiliary table api_keys exists (for external service keys) ---
            # Structure: id (PK), name (unique), key (text)
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    "key" TEXT
                )
                """
            )
            # Seed default entry for consultacro.com.br if missing
            # Using INSERT OR IGNORE to avoid duplicate based on UNIQUE(name)
            conn.exec_driver_sql(
                """
                INSERT OR IGNORE INTO api_keys (name, "key")
                VALUES ('consultacro.com.br', '1905229841')
                """
            )
    except OperationalError:
        # Best effort only; ignore if not SQLite or other unexpected engine errors
        pass
