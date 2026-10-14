"""Add pay-period comments columns.

Revision ID: 008
Revises: 007
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pay_periods", sa.Column("comments", sa.Text(), nullable=True))
    op.add_column("pay_periods", sa.Column("comments2", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pay_periods", "comments2")
    op.drop_column("pay_periods", "comments")
