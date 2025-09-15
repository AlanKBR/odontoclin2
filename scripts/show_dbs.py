"""
Mostra o conteúdo de todos os bancos SQLite em `instance/` de forma simples e estruturada.

Uso rápido:
    python scripts/show_dbs.py              # lista todos os bancos, até 10 linhas por tabela
    python scripts/show_dbs.py --limit 5    # limita a 5 linhas por tabela
    python scripts/show_dbs.py --db pacientes.db --table pacientes  # filtra banco/tabela
    python scripts/show_dbs.py --schema-only # mostra apenas esquema (colunas/índices)

Opções principais:
    --db           Nome do arquivo .db para filtrar (pode repetir a flag)
    --table        Nome da tabela para filtrar (pode repetir a flag)
    --limit        Número de linhas por tabela (padrão: 10)
    --max-width    Largura máxima por coluna para impressão (padrão: 40)
    --schema-only  Mostra apenas esquema, sem linhas

Observações:
- Saída amigável para terminal, sem dependências externas.
- Trunca conteúdo longo com “…” e representa valores nulos como ␀.
- Tenta lidar com BLOBs mostrando tamanho em bytes.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from typing import List, Sequence, Tuple

# Caminho da pasta instance/ relativo a este arquivo (scripts/ -> raiz -> instance/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

NULL_STR = "␀"  # representação para None/NULL
ELLIPSIS = "…"


def find_dbs(filters: Sequence[str] | None = None) -> List[str]:
    if not os.path.isdir(INSTANCE_DIR):
        return []
    all_dbs = [f for f in os.listdir(INSTANCE_DIR) if f.endswith(".db")]
    if not filters:
        return sorted(all_dbs)
    flt = {f.lower() for f in filters}
    return sorted([f for f in all_dbs if f.lower() in flt])


def fetch_tables(conn: sqlite3.Connection, table_filters: Sequence[str] | None = None) -> List[str]:
    cur = conn.execute(
        (
            "SELECT name FROM sqlite_master "
            "WHERE type in ('table','view') "
            "AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
    )
    names = [r[0] for r in cur.fetchall()]
    if table_filters:
        tf = {t.lower() for t in table_filters}
        names = [n for n in names if n.lower() in tf]
    return names


def truncate(text: str, width: int) -> str:
    if width <= 1:
        return text[:width]
    return text if len(text) <= width else text[: max(0, width - 1)] + ELLIPSIS


def value_to_str(v, max_width: int) -> str:
    if v is None:
        return NULL_STR
    if isinstance(v, bytes):
        # Mostra tamanho e início em hex
        head = v[:8].hex()
        s = f"<{len(v)} bytes: {head}…>" if len(v) > 8 else f"<{len(v)} bytes: {head}>"
        return truncate(s, max_width)
    s = str(v)
    # Sanitiza para não quebrar a tabela no terminal
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    s = "".join(ch if ch.isprintable() else " " for ch in s)
    s = " ".join(s.split())  # colapsa espaços repetidos
    return truncate(s, max_width)


def format_table(headers: Sequence[str], rows: Sequence[Sequence], max_width: int) -> str:
    # Calcula largura por coluna respeitando max_width
    widths = [min(max(len(h), 1), max_width) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            s = value_to_str(cell, max_width)
            widths[i] = min(max(widths[i], len(s)), max_width)

    def fmt_row(vals: Sequence[str]) -> str:
        parts = [str(vals[i]).ljust(widths[i]) for i in range(len(headers))]
        return " | ".join(parts)

    sep = "-+-".join("-" * w for w in widths)
    out_lines = [fmt_row(headers), sep]
    for row in rows:
        out_lines.append(fmt_row([value_to_str(c, max_width) for c in row]))
    return "\n".join(out_lines)


def print_schema(conn: sqlite3.Connection, table: str) -> None:
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    cols = cur.fetchall()  # cid, name, type, notnull, dflt_value, pk
    if cols:
        headers = ["cid", "name", "type", "notnull", "default", "pk"]
        rows = cols
        print("    Colunas:")
        print(indent(format_table(headers, rows, max_width=40), 6))
    idx = conn.execute(f"PRAGMA index_list('{table}')").fetchall()
    if idx:
        print("    Índices:")
        for row in idx:
            # (seq, name, unique, origin, partial)
            name = row[1]
            unique = bool(row[2])
            print(indent(f"- {name}{' (UNIQUE)' if unique else ''}", 6))
    fk = conn.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
    if fk:
        print("    Chaves estrangeiras:")
        for row in fk:
            # (id, seq, table, from, to, on_update, on_delete, match)
            rid, _, ref_table, col_from, col_to, on_upd, on_del, match = row
            txt = f"- {col_from} -> {ref_table}.{col_to}"
            if on_upd or on_del:
                txt += f" (on_update={on_upd or '-'}, on_delete={on_del or '-'})"
            print(indent(txt, 6))


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


def show_db(
    db_file: str,
    table_filters: Sequence[str] | None,
    limit: int,
    max_width: int,
    schema_only: bool,
) -> None:
    path = os.path.join(INSTANCE_DIR, db_file)
    print(f"\n=== Banco: {db_file} ===")
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"  ERRO ao abrir {db_file}: {e}")
        return

    try:
        tables = fetch_tables(conn, table_filters)
        if not tables:
            print("  (Sem tabelas)")
            return
        for t in tables:
            print(f"\n  Tabela: {t}")
            # Esquema
            print_schema(conn, t)
            if schema_only:
                continue
            # Contagem
            try:
                total = conn.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
            except Exception as e:
                print(indent(f"(Não foi possível contar linhas: {e})", 4))
                total = None
            if total is not None:
                print(indent(f"Registros: {total}", 4))
            # Linhas
            try:
                cur = conn.execute(f"SELECT * FROM '{t}' LIMIT ?", (limit,))
                headers = [d[0] for d in cur.description]
                rows = cur.fetchall()
                if rows:
                    print(indent(format_table(headers, rows, max_width), 4))
                else:
                    print(indent("(Sem dados)", 4))
            except Exception as e:
                print(indent(f"(Erro ao listar dados: {e})", 4))
    finally:
        conn.close()


def parse_args(argv: Sequence[str]) -> Tuple[List[str] | None, List[str] | None, int, int, bool]:
    import argparse

    p = argparse.ArgumentParser(
        prog="show_dbs",
        description="Lista conteúdo dos bancos SQLite em instance/",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--db", action="append", help="Nome do arquivo .db para filtrar (repetível)")
    p.add_argument("--table", action="append", help="Nome da tabela para filtrar (repetível)")
    p.add_argument("--limit", type=int, default=10, help="Linhas por tabela (padrão: 10)")
    p.add_argument(
        "--max-width",
        type=int,
        default=40,
        help="Largura máxima por coluna (padrão: 40)",
    )
    p.add_argument(
        "--schema-only",
        action="store_true",
        help="Mostra apenas o esquema (colunas/índices), sem dados",
    )
    args = p.parse_args(list(argv))
    return args.db, args.table, args.limit, args.max_width, args.schema_only


def main(argv: Sequence[str] | None = None) -> int:
    db_filters, table_filters, limit, max_width, schema_only = parse_args(argv or sys.argv[1:])

    if not os.path.isdir(INSTANCE_DIR):
        print(f"Pasta 'instance' não encontrada em: {INSTANCE_DIR}")
        return 2

    dbs = find_dbs(db_filters)
    if not dbs:
        all_found = os.listdir(INSTANCE_DIR) if os.path.isdir(INSTANCE_DIR) else []
        print("Nenhum arquivo .db encontrado em 'instance/'.")
        if all_found:
            print("Arquivos disponíveis:")
            for f in all_found:
                print(" -", f)
        return 1

    for db_file in dbs:
        show_db(db_file, table_filters, limit, max_width, schema_only)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
