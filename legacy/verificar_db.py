#!/usr/bin/env python3
"""
verificar_db.py

Exibe no terminal, de forma organizada e simples, a estrutura de TODOS os bancos
SQLite (*.db) presentes na pasta `instance` (dinâmico).

Uso:
  python verificar_db.py               # varre a pasta instance padrão
  python verificar_db.py <pasta>       # varre a pasta informada

Saída (resumo por banco):
- Nome do arquivo e caminho
- Lista de tabelas (com contagem de linhas)
- Para cada tabela: colunas (tipo, PK, NOT NULL, DEFAULT), chaves estrangeiras e índices
- Lista de views (se houver)
"""

from __future__ import annotations

import glob
import os
import sqlite3
import sys
from typing import List, Tuple


def human_path(p: str) -> str:
    try:
        return os.path.relpath(p, start=os.getcwd())
    except Exception:
        return p


def find_instance_dir(base_dir: str) -> str:
    """Resolve a pasta `instance` com base no local do script, por padrão.
    Se um argumento de pasta for passado, usa-o diretamente.
    """
    return os.path.abspath(os.path.join(base_dir, "instance"))


def list_db_files(target_dir: str) -> List[str]:
    pattern = os.path.join(target_dir, "*.db")
    files = sorted(glob.glob(pattern))
    return files


def fetch_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    )
    return [r[0] for r in cur.fetchall()]


def fetch_views(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;")
    return [r[0] for r in cur.fetchall()]


def fetch_columns(conn: sqlite3.Connection, table: str) -> List[Tuple]:
    # cid, name, type, notnull, dflt_value, pk
    cur = conn.execute(f"PRAGMA table_info('{table.replace("'", "''")}')")
    return cur.fetchall()


def fetch_foreign_keys(conn: sqlite3.Connection, table: str) -> List[Tuple]:
    # id, seq, table, from, to, on_update, on_delete, match
    cur = conn.execute(f"PRAGMA foreign_key_list('{table.replace("'", "''")}')")
    return cur.fetchall()


def fetch_indices(conn: sqlite3.Connection, table: str) -> List[Tuple]:
    # seq, name, unique, origin, partial
    cur = conn.execute(f"PRAGMA index_list('{table.replace("'", "''")}')")
    return cur.fetchall()


def fetch_index_info(conn: sqlite3.Connection, index_name: str) -> List[Tuple]:
    # seqno, cid, name
    cur = conn.execute(f"PRAGMA index_info('{index_name.replace("'", "''")}')")
    return cur.fetchall()


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM '{table.replace("'", "''")}'")
        return int(cur.fetchone()[0])
    except Exception:
        return -1


def print_header(title: str) -> None:
    line = "=" * len(title)
    print(line)
    print(title)
    print(line)


def print_subheader(title: str) -> None:
    print(f"\n- {title}")


def describe_database(db_path: str) -> None:
    db_name = os.path.basename(db_path)
    title = f"Banco: {db_name}  |  Caminho: {human_path(db_path)}"
    print_header(title)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"Erro ao abrir o banco: {e}")
        return

    try:
        tables = fetch_tables(conn)
        views = fetch_views(conn)

        print_subheader(f"Tabelas ({len(tables)})")
        if not tables:
            print("  (nenhuma tabela)")
        for t in tables:
            qtd = count_rows(conn, t)
            qtd_str = f"{qtd}" if qtd >= 0 else "?"
            print(f"  • {t} (linhas: {qtd_str})")

            cols = fetch_columns(conn, t)
            if cols:
                print("    colunas:")
                for cid, name, ctype, notnull, dflt, pk in cols:
                    parts = [ctype or "?"]
                    if pk:
                        parts.append("PK")
                    if notnull:
                        parts.append("NOT NULL")
                    if dflt is not None:
                        parts.append(f"DEFAULT {dflt}")
                    meta = ", ".join(parts)
                    print(f"      - {name}: {meta}")
            else:
                print("    (sem colunas?)")

            fks = fetch_foreign_keys(conn, t)
            if fks:
                print("    chaves estrangeiras:")
                for _id, _seq, ref_table, frm, to, on_upd, on_del, match in fks:
                    extras = []
                    if on_upd and on_upd.upper() != "NO ACTION":
                        extras.append(f"ON UPDATE {on_upd}")
                    if on_del and on_del.upper() != "NO ACTION":
                        extras.append(f"ON DELETE {on_del}")
                    if match and match.upper() != "NONE":
                        extras.append(f"MATCH {match}")
                    extra = f" ({'; '.join(extras)})" if extras else ""
                    print(f"      - {frm} -> {ref_table}({to}){extra}")
            else:
                print("    chaves estrangeiras: nenhuma")

            idxs = fetch_indices(conn, t)
            if idxs:
                print("    índices:")
                for _seq, idx_name, unique, origin, partial in idxs:
                    cols_info = fetch_index_info(conn, idx_name)
                    cols_list = ", ".join([cname for (_s, _cid, cname) in cols_info]) or "?"
                    uniq = "unique" if unique else "normal"
                    print(f"      - {idx_name} ({uniq}) colunas: {cols_list}")
            else:
                print("    índices: nenhum")

        print_subheader(f"Views ({len(views)})")
        if views:
            for v in views:
                print(f"  • {v}")
        else:
            print("  (nenhuma view)")

    except Exception as e:
        print(f"Erro ao inspecionar o banco: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main() -> int:
    # Pasta alvo: argumento 1 (opcional) ou ./instance relativo a este script
    arg_dir = sys.argv[1] if len(sys.argv) > 1 else None
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.abspath(arg_dir) if arg_dir else find_instance_dir(base_dir)

    if not os.path.isdir(target_dir):
        print(f"Pasta não encontrada: {target_dir}")
        return 2

    db_files = list_db_files(target_dir)
    if not db_files:
        print(f"Nenhum arquivo .db encontrado em: {human_path(target_dir)}")
        return 0

    print(f"Encontrados {len(db_files)} arquivo(s) .db em {human_path(target_dir)}\n")

    for i, db_path in enumerate(db_files, start=1):
        describe_database(db_path)
        if i < len(db_files):
            print("\n")  # separador entre bancos

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
