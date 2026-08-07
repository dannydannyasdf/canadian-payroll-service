"""Initial baseline schema (Phases 1-5).

Revision ID: 001
Revises:
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sin", sa.String(length=11), nullable=False),
        sa.ForeignKeyConstraint(["employer_id"], ["employers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employer_id", "sin", name="uq_employee_employer_sin"),
    )
    op.create_table(
        "pay_periods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=False),
        sa.Column("gross_pay", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cpp", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("ei", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("income_tax", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("net_pay", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id",
            "period_start",
            "period_end",
            name="uq_pay_period_employee_dates",
        ),
    )
    op.create_table(
        "ytd_totals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("gross_pay", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cpp", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("ei", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("income_tax", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("net_pay", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("last_period_start", sa.Date(), nullable=True),
        sa.Column("last_period_end", sa.Date(), nullable=True),
        sa.Column("last_pay_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "tax_year", name="uq_ytd_employee_year"),
    )
    op.create_table(
        "billing_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consumer_username", sa.String(length=128), nullable=False),
        sa.Column("gross_pay", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("billing_fee", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("billing_events")
    op.drop_table("ytd_totals")
    op.drop_table("pay_periods")
    op.drop_table("employees")
    op.drop_table("employers")
