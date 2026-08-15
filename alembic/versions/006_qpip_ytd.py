"""Add QPIP columns for Québec payroll deductions.

Revision ID: 006
Revises: 005
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, Sequence[str], None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pay_periods",
        sa.Column("qpip", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
    )
    op.add_column(
        "ytd_totals",
        sa.Column("qpip", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
    )
    op.alter_column("pay_periods", "qpip", server_default=None)
    op.alter_column("ytd_totals", "qpip", server_default=None)


def downgrade() -> None:
    op.drop_column("ytd_totals", "qpip")
    op.drop_column("pay_periods", "qpip")
