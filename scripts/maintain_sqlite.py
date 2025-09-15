"""
Manutenção e backup dos bancos SQLite em instance/.

Comandos disponíveis:
  - wal:        Habilita journal_mode=WAL para todos os .db (persistente)
  - optimize:   Executa VACUUM e ANALYZE (opcionalmente com page_size)
  - backup:     Faz backup seguro (sqlite3.Connection.backup) de todos os .db

Exemplos:
  python scripts/maintain_sqlite.py wal
  python scripts/maintain_sqlite.py optimize --page-size 4096
  python scripts/maintain_sqlite.py backup --out-dir backups

Observações:
- journal_mode=WAL melhora concorrência e evita bloqueios de leitura.
- VACUUM pode reescrever arquivos; execute com app parado para máximo efeito.
- BACKUP usa API nativa do SQLite e funciona mesmo com WAL.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, List

BASE_DIR = Path(__file__).resolve().parents[1]
INSTANCE_DIR = BASE_DIR / "instance"


def _list_dbs(filters: Iterable[str] | None = None) -> List[Path]:
    if not INSTANCE_DIR.is_dir():
        return []
    dbs = sorted(p for p in INSTANCE_DIR.glob("*.db"))
    if not filters:
        return dbs
    flt = {f.lower() for f in filters}
    return [p for p in dbs if p.name.lower() in flt]


def _open(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    return conn


def cmd_wal(dbs: List[Path]) -> int:
    code = 0
    for db in dbs:
        try:
            with _open(db) as conn:
                cur = conn.execute("PRAGMA journal_mode=WAL")
                mode = cur.fetchone()[0]
                conn.execute("PRAGMA synchronous=NORMAL")
            print(f"[OK] {db.name}: journal_mode={mode}")
        except Exception as e:
            print(f"[ERRO] {db.name}: {e}")
            code = 1
    return code


def cmd_optimize(dbs: List[Path], page_size: int | None) -> int:
    code = 0
    for db in dbs:
        try:
            with _open(db) as conn:
                if page_size:
                    conn.execute(f"PRAGMA page_size={int(page_size)}")
                conn.execute("PRAGMA optimize")
                conn.execute("ANALYZE")
                conn.execute("VACUUM")
            print(f"[OK] {db.name}: optimize{' + VACUUM' if page_size else ''}")
        except Exception as e:
            print(f"[ERRO] {db.name}: {e}")
            code = 1
    return code


def cmd_backup(dbs: List[Path], out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    code = 0
    for db in dbs:
        dest = out_dir / f"{db.stem}.{stamp}.db"
        try:
            with _open(db) as src, sqlite3.connect(dest) as dst:
                src.backup(dst)
            print(f"[OK] backup: {db.name} -> {dest.relative_to(BASE_DIR)}")
        except Exception as e:
            print(f"[ERRO] backup {db.name}: {e}")
            code = 1
    return code


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Manutenção dos bancos SQLite em instance/")
    sub = p.add_subparsers(dest="cmd", required=True)

    p.add_argument(
        "--db",
        action="append",
        help="Filtra por nome de arquivo .db (repetível)",
    )

    _ = sub.add_parser("wal", help="Habilita journal_mode=WAL + synchronous=NORMAL")

    s_opt = sub.add_parser("optimize", help="PRAGMA optimize + ANALYZE + VACUUM")
    s_opt.add_argument("--page-size", type=int, help="Define PRAGMA page_size antes do VACUUM")

    s_bak = sub.add_parser("backup", help="Backup seguro de todos os .db")
    s_bak.add_argument(
        "--out-dir",
        type=Path,
        default=BASE_DIR / "instance" / "backups",
        help="Pasta de destino (padrão: instance/backups)",
    )

    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    dbs = _list_dbs(args.db)
    if not dbs:
        print(f"Nenhum .db encontrado em {INSTANCE_DIR}")
        return 2

    if args.cmd == "wal":
        return cmd_wal(dbs)
    if args.cmd == "optimize":
        return cmd_optimize(dbs, getattr(args, "page_size", None))
    if args.cmd == "backup":
        return cmd_backup(dbs, getattr(args, "out_dir"))

    print("Comando inválido")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
