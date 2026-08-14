"""Set demo sample employee Jane to Quebec employment province.

Revision ID: 004
Revises: 003
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_SAMPLE_SIN = "130-692-544"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE employees
            SET employment_province = 'QC'
            WHERE sin = :sin
              AND (employment_province IS NULL OR employment_province != 'QC')
            """
        ).bindparams(sin=DEMO_SAMPLE_SIN)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE employees
            SET employment_province = NULL
            WHERE sin = :sin AND employment_province = 'QC'
            """
        ).bindparams(sin=DEMO_SAMPLE_SIN)
    )
