"""Add Relevé 1 slip number storage and sequence counter.

Revision ID: 005
Revises: 004
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_SEQ_BASE = 71_997_012


def upgrade() -> None:
    op.add_column(
        "ytd_totals",
        sa.Column("rq_releve_no", sa.String(length=9), nullable=True),
    )
    op.create_table(
        "rq_releve_sequence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("next_base", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text("INSERT INTO rq_releve_sequence (id, next_base) VALUES (1, :base)").bindparams(
            base=DEFAULT_SEQ_BASE
        )
    )


def downgrade() -> None:
    op.drop_table("rq_releve_sequence")
    op.drop_column("ytd_totals", "rq_releve_no")
