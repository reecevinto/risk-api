"""add subscription current period start

Revision ID: 903267aa7fb0
Revises: dc12f2d5a04c
Create Date: 2026-07-20 21:54:09.605255
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "903267aa7fb0"
down_revision: Union[str, Sequence[str], None] = "dc12f2d5a04c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column(
            "current_period_start",
            sa.DateTime(),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column(
        "subscriptions",
        "current_period_start"
    )