"""
Remove a coluna 'updated_at' da tabela 'app_settings' em instance/calendario.db.

Uso:
  python scripts/migrate_calendario_drop_updated_at.py

- Cria uma cópia de backup antes de alterar: calendario.db.bak-YYYYmmddHHMMSS
- Opera de forma idempotente: se a coluna já não existir, apenas informa e sai com sucesso.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_FILE = os.path.join(INSTANCE_DIR, "calendario.db")


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    return any(row[1] == column for row in cur.fetchall())


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        ("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') " "AND name = ? LIMIT 1"),
        (table,),
    )
    return cur.fetchone() is not None


def backup(db_path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    dst = f"{db_path}.bak-{ts}"
    shutil.copy2(db_path, dst)
    return dst


def migrate() -> int:
    if not os.path.isfile(DB_FILE):
        print(f"Arquivo não encontrado: {DB_FILE}")
        return 2

    conn = sqlite3.connect(DB_FILE)
    try:
        if not table_exists(conn, "app_settings"):
            print("Tabela 'app_settings' não existe em calendario.db. Nada a fazer.")
            return 0
        if not column_exists(conn, "app_settings", "updated_at"):
            print("Coluna 'updated_at' já não existe. Nada a fazer.")
            return 0

        bkp = backup(DB_FILE)
        print(f"Backup criado: {bkp}")

        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=off")
        cur.execute("BEGIN")
        try:
            # Cria nova tabela sem a coluna updated_at
            cur.execute(
                (
                    "CREATE TABLE app_settings__new (\n"
                    "  key VARCHAR(100) PRIMARY KEY NOT NULL,\n"
                    "  value VARCHAR(1000)\n"
                    ")"
                )
            )
            # Copia dados
            cur.execute(
                "INSERT INTO app_settings__new (key, value) SELECT key, value FROM app_settings"
            )
            # Remove antiga e renomeia
            cur.execute("DROP TABLE app_settings")
            cur.execute("ALTER TABLE app_settings__new RENAME TO app_settings")

            cur.execute("COMMIT")
            print("Migração concluída com sucesso: coluna 'updated_at' removida.")
        except Exception as e:
            cur.execute("ROLLBACK")
            print(f"Erro na migração, banco restaurado a partir do backup: {e}")
            return 1
        finally:
            cur.execute("PRAGMA foreign_keys=on")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(migrate())
