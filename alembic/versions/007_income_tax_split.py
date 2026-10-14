"""Split income tax into federal and provincial columns.

Revision ID: 007
Revises: 006
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("pay_periods", "ytd_totals"):
        op.add_column(
            table,
            sa.Column(
                "federal_income_tax",
                sa.Numeric(precision=12, scale=2),
                nullable=False,
                server_default="0",
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "provincial_income_tax",
                sa.Numeric(precision=12, scale=2),
                nullable=False,
                server_default="0",
            ),
        )

    op.execute(
        """
        UPDATE pay_periods
        SET federal_income_tax = income_tax,
            provincial_income_tax = 0
        """
    )
    op.execute(
        """
        UPDATE ytd_totals
        SET federal_income_tax = income_tax,
            provincial_income_tax = 0
        """
    )

    for table in ("pay_periods", "ytd_totals"):
        op.alter_column(table, "federal_income_tax", server_default=None)
        op.alter_column(table, "provincial_income_tax", server_default=None)


def downgrade() -> None:
    op.drop_column("ytd_totals", "provincial_income_tax")
    op.drop_column("ytd_totals", "federal_income_tax")
    op.drop_column("pay_periods", "provincial_income_tax")
    op.drop_column("pay_periods", "federal_income_tax")
