"""
Safely back up and fix the users.db schema to match current models.

This calls app.auth.upgrade.ensure_users_schema() to add missing columns and
create the table if it doesn't exist, without dropping data.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app import create_app


def backup_users_db(base_dir: Path) -> Path | None:
    inst = base_dir / "instance"
    src = inst / "users.db"
    if not src.exists():
        return None
    bak = inst / f"users.db.bak-fix-{Path(__file__).stem}"
    shutil.copy2(src, bak)
    return bak


def main() -> int:
    app = create_app()
    base_dir = Path(__file__).resolve().parents[1]
    bak = backup_users_db(base_dir)
    if bak:
        print(f"Backup created: {bak}")
    with app.app_context():
        from app.auth.upgrade import ensure_users_schema

        ensure_users_schema()
        print("users schema ensured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
