"""Serviços de lookup (dentistas e pacientes) usados pelas rotas da agenda.

Centraliza consultas raw em SQLite para facilitar futura migração para
SQLAlchemy/ORM completo ou cache externo.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from flask import current_app

# -------- Utilidades --------


def _db_path(name: str) -> str:
    base = getattr(current_app, "instance_path", current_app.root_path)
    return os.path.join(base, name)


# -------- Dentistas --------


def list_dentists() -> tuple[list[dict[str, Any]], str]:
    """Retorna (lista, etag_token) para cabeçalho condicional.

    Mantém lógica do legacy: detecta colunas dinamicamente e filtra por
    ativos e cargo (dentista/admin) se existir.
    """
    path = _db_path("users.db")
    dentists: list[dict[str, Any]] = []
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in cur.fetchall()]
            if "id" in cols:
                name_candidates = [
                    "nome_profissional",
                    "nome",
                    "nome_completo",
                    "name",
                    "full_name",
                    "username",
                ]
                name_col = next(
                    (c for c in name_candidates if c in cols),
                    "id",
                )
                color_col = "color" if "color" in cols else ("cor" if "cor" in cols else None)
                sel_cols = [
                    "id",
                    name_col,
                ] + ([color_col] if color_col else [])
                conditions: list[str] = []
                if "is_active" in cols:
                    conditions.append("is_active = 1")
                if "ativo" in cols:  # novo modelo
                    conditions.append("ativo = 1")
                if "cargo" in cols:
                    conditions.append("cargo IN ('dentista','admin')")
                where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
                q = f"SELECT {', '.join(sel_cols)} FROM users{where} " f"ORDER BY {name_col}"
                cur.execute(q)
                for r in cur.fetchall():
                    dentists.append(
                        {
                            "id": r[0],
                            "nome": r[1],
                            "color": r[2] if color_col else None,
                        }
                    )
        finally:  # pragma: no cover - best effort close
            try:
                conn.close()
            except Exception:
                pass
    etag = f"{int(os.path.getmtime(path)) if os.path.exists(path) else 0}:" f"{len(dentists)}"
    return dentists, etag


# -------- Pacientes básicos --------


def list_pacientes_basic() -> list[dict[str, Any]]:
    path = _db_path("pacientes.db")
    if not os.path.exists(path):
        return []
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master " "WHERE type='table' AND name='pacientes'")
        if not cur.fetchone():  # tabela não existe
            return []
        cur.execute("SELECT id, nome FROM pacientes ORDER BY nome")
        return [{"id": row[0], "nome": row[1]} for row in cur.fetchall() if row and row[1]]
    finally:  # pragma: no cover
        try:
            conn.close()
        except Exception:
            pass


def search_paciente_names(query: str, limit: int = 20) -> list[str]:
    q = (query or "").strip()
    if not q:
        return []
    path = _db_path("pacientes.db")
    if not os.path.exists(path):
        return []
    nomes: list[str] = []
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            (
                "SELECT nome FROM pacientes "
                "WHERE (nome LIKE ? COLLATE NOCASE) "
                "OR (nome LIKE ? COLLATE NOCASE) "
                "ORDER BY nome LIMIT ?"
            ),
            (f"{q}%", f"% {q}%", limit),
        )
        for row in cur.fetchall():
            if row and row[0]:
                nomes.append(row[0])
    finally:  # pragma: no cover
        try:
            conn.close()
        except Exception:
            pass
    return nomes[:limit]


def find_paciente_phone(nome: str) -> str | None:
    name = (nome or "").strip()
    if not name:
        return None
    path = _db_path("pacientes.db")
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT celular FROM pacientes " "WHERE LOWER(nome) = LOWER(?) LIMIT 1",
            (name,),
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                ("SELECT celular FROM pacientes " "WHERE LOWER(nome) LIKE LOWER(?) LIMIT 1"),
                (f"%{name}%",),
            )
            row = cur.fetchone()
        if row and row[0]:
            return row[0]
        return None
    finally:  # pragma: no cover
        try:
            conn.close()
        except Exception:
            pass
