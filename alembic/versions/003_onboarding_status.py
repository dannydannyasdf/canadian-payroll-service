"""Add onboarding status and employee employment province.

Revision ID: 003
Revises: 002
Create Date: 2026-08-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employers",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
    )
    op.add_column(
        "employers",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(sa.text("UPDATE employers SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))

    op.add_column(
        "employees",
        sa.Column("employment_province", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
    )
    op.add_column(
        "employees",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(sa.text("UPDATE employees SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))


def downgrade() -> None:
    op.drop_column("employees", "created_at")
    op.drop_column("employees", "status")
    op.drop_column("employees", "employment_province")
    op.drop_column("employers", "created_at")
    op.drop_column("employers", "status")
