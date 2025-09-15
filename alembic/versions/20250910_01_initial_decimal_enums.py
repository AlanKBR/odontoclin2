"""Initial migration.

Introduz Decimal em campos monetários, vínculo opcional de
financeiro->procedimento e constraints simples de enum.

Revision ID: 20250910_01
Revises:
Create Date: 2025-09-10
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from alembic import op as _op  # type: ignore[attr-defined]

op: Any = _op

# revision identifiers, used by Alembic.
revision = "20250910_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # Example operations (idempotent guards kept minimal for SQLite dev)
    with op.batch_alter_table("plano_tratamento") as batch:
        batch.alter_column("orcamento_total", type_=sa.Numeric(12, 2))
    with op.batch_alter_table("procedimentos") as batch:
        batch.alter_column("valor", type_=sa.Numeric(12, 2))
    with op.batch_alter_table("financeiro") as batch:
        batch.alter_column("valor", type_=sa.Numeric(12, 2))
        batch.add_column(sa.Column("procedimento_id", sa.Integer(), nullable=True))
        batch.create_check_constraint("ck_financeiro_tipo", "tipo in ('Crédito','Débito')")
        batch.create_check_constraint(
            "ck_financeiro_status",
            "status in ('Pendente','Pago','Cancelado')",
        )


def downgrade() -> None:
    with op.batch_alter_table("financeiro") as batch:
        batch.drop_constraint("ck_financeiro_tipo", type_="check")
        batch.drop_constraint("ck_financeiro_status", type_="check")
        batch.drop_column("procedimento_id")
        batch.alter_column("valor", type_=sa.Float())
    with op.batch_alter_table("procedimentos") as batch:
        batch.alter_column("valor", type_=sa.Float())
    with op.batch_alter_table("plano_tratamento") as batch:
        batch.alter_column("orcamento_total", type_=sa.Float())
