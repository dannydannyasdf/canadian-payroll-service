"""Add employer and employee fields for T4 / Relevé 1 slips.

Revision ID: 002
Revises: 001
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employers", sa.Column("business_number", sa.String(length=15), nullable=True))
    op.add_column("employers", sa.Column("payroll_account_number", sa.String(length=20), nullable=True))
    op.add_column("employers", sa.Column("address_line1", sa.String(length=255), nullable=True))
    op.add_column("employers", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("employers", sa.Column("province", sa.String(length=2), nullable=True))
    op.add_column("employers", sa.Column("postal_code", sa.String(length=7), nullable=True))

    op.add_column("employees", sa.Column("address_line1", sa.String(length=255), nullable=True))
    op.add_column("employees", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("employees", sa.Column("province", sa.String(length=2), nullable=True))
    op.add_column("employees", sa.Column("postal_code", sa.String(length=7), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "postal_code")
    op.drop_column("employees", "province")
    op.drop_column("employees", "city")
    op.drop_column("employees", "address_line1")

    op.drop_column("employers", "postal_code")
    op.drop_column("employers", "province")
    op.drop_column("employers", "city")
    op.drop_column("employers", "address_line1")
    op.drop_column("employers", "payroll_account_number")
    op.drop_column("employers", "business_number")
