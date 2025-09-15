"""Adiciona coluna criado_em à tabela modelos_receita (bind receitas).

Script manual temporário até adoção de Alembic. Ignora se coluna já existir.
"""

from datetime import datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError


def add_column_if_missing(engine):
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("modelos_receita")]
    if "criado_em" in cols:
        print("[info] Coluna criado_em já existe; nada a fazer.")
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE modelos_receita ADD COLUMN " "criado_em DATETIME"))
            # Opcional: preencher timestamp atual nos registros existentes
            conn.execute(
                text("UPDATE modelos_receita SET criado_em = :agora " "WHERE criado_em IS NULL"),
                {"agora": datetime.utcnow()},
            )
        print("[ok] Coluna criado_em adicionada e valores preenchidos.")
    except OperationalError as exc:  # pragma: no cover
        print(f"[erro] Falha ao adicionar coluna: {exc}")


def main():  # pragma: no cover
    engine = create_engine("sqlite:///instance/receitas.db")
    add_column_if_missing(engine)


if __name__ == "__main__":  # pragma: no cover
    main()
