"""
fix request log timestamp default

Revision ID: 0ebfb8e06282
Revises: 7c394b4452d2

Day 7 – Phase 2

Ensures every new request log automatically receives
the current timestamp.

This fixes dashboards showing:

    🕒 --

instead of the actual request time.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ==========================================================
# Revision identifiers
# ==========================================================

revision: str = "0ebfb8e06282"
down_revision: Union[str, Sequence[str], None] = "7c394b4452d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==========================================================
# UPGRADE
# ==========================================================

def upgrade() -> None:
    """
    Add a database default to request_logs.created_at.

    Existing rows remain unchanged.

    All future INSERT operations automatically receive
    the current timestamp.
    """

    op.alter_column(
        "request_logs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        existing_nullable=True,
    )


# ==========================================================
# DOWNGRADE
# ==========================================================

def downgrade() -> None:
    """
    Remove the automatic timestamp.
    """

    op.alter_column(
        "request_logs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=True,
    )