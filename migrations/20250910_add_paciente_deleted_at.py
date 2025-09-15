"""Adiciona coluna deleted_at à tabela pacientes.

Script manual de migração simples (sem Alembic). Execute uma vez após deploy
em ambientes que já possuam a tabela 'pacientes'. Ignora se coluna já existe.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError


def add_column_if_missing(engine):
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("pacientes")]
    if "deleted_at" in cols:
        print("[info] Coluna deleted_at já existe; nada a fazer.")
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE pacientes ADD COLUMN deleted_at DATETIME"))
        print("[ok] Coluna deleted_at adicionada.")
    except OperationalError as exc:  # pragma: no cover - ambiente específico
        print(f"[erro] Falha ao adicionar coluna: {exc}")


def main():  # pragma: no cover - script utilitário
    # Ajuste conforme config real de produção
    url = "sqlite:///instance/pacientes.db"
    engine = create_engine(url)
    add_column_if_missing(engine)


if __name__ == "__main__":  # pragma: no cover
    main()
