"""
One-off migration: move calendar_event and holidays tables from app.db to calendario.db.

Per request: do NOT transfer data. Simply drop from app.db and create in calendario.db.

Usage (from repo root or this folder):
  python -m agenda.migrate_move_calendar_to_calendario
or
  python agenda/migrate_move_calendar_to_calendario.py
"""

from __future__ import annotations

import os
import sqlite3


def instance_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base, os.pardir, "instance"))


def drop_from_app_db(inst_dir: str) -> None:
    app_db = os.path.join(inst_dir, "app.db")
    os.makedirs(os.path.dirname(app_db), exist_ok=True)
    conn = sqlite3.connect(app_db)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=OFF;")
        # Drop if exists
        for tbl in ("calendar_event", "holidays"):
            try:
                cur.execute(f"DROP TABLE IF EXISTS {tbl};")
                print(f"Dropped {tbl} from app.db (if existed).")
            except Exception as e:
                print(f"Warning: could not drop {tbl} from app.db: {e}")
        conn.commit()
    finally:
        conn.close()


def create_in_calendario_db(inst_dir: str) -> None:
    cal_db = os.path.join(inst_dir, "calendario.db")
    os.makedirs(os.path.dirname(cal_db), exist_ok=True)
    conn = sqlite3.connect(cal_db)
    try:
        cur = conn.cursor()
        # Create calendar_event table (if not exists)
        cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS calendar_event ("
                "id INTEGER PRIMARY KEY,"
                "title VARCHAR(120) NOT NULL,"
                "start VARCHAR(30) NOT NULL,"
                "end VARCHAR(30) NOT NULL,"
                "color VARCHAR(20),"
                "notes VARCHAR(500),"
                "profissional_id INTEGER"
                ");"
            )
        )
        # Create holidays table (if not exists)
        cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS holidays ("
                "date VARCHAR(10) PRIMARY KEY,"
                "name VARCHAR(200) NOT NULL,"
                "type VARCHAR(50),"
                "level VARCHAR(50),"
                "state VARCHAR(5),"
                "year INTEGER NOT NULL,"
                "source VARCHAR(50) NOT NULL DEFAULT 'invertexto',"
                "updated_at DATETIME"
                ");"
            )
        )
        conn.commit()
        print("Ensured tables exist in calendario.db: calendar_event, holidays")
    finally:
        conn.close()


def main() -> int:
    inst_dir = instance_path()
    if not os.path.isdir(inst_dir):
        print(f"Instance folder not found: {inst_dir}")
        return 2
    print(f"Using instance folder: {inst_dir}")
    drop_from_app_db(inst_dir)
    create_in_calendario_db(inst_dir)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
