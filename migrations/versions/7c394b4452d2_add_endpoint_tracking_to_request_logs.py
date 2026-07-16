"""add endpoint tracking to request logs

Revision ID: 7c394b4452d2
Revises: 64cbfd587526

Day 7 – Phase 2
Usage Analytics Engine

Adds endpoint tracking so every API request knows
which endpoint generated it. This enables:

• Endpoint popularity
• Endpoint usage breakdown
• Average risk per endpoint
• Overage per endpoint
• Dashboard analytics
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ==========================================================
# Revision identifiers
# ==========================================================

revision: str = "7c394b4452d2"
down_revision: Union[str, Sequence[str], None] = "64cbfd587526"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ==========================================================
# UPGRADE
# ==========================================================

def upgrade() -> None:
    """
    Add endpoint tracking to request_logs.

    Existing rows are first given a temporary default so the
    NOT NULL constraint can be added safely.

    After all existing rows are populated, the temporary
    default is removed.
    """

    # ------------------------------------------------------
    # Add endpoint column
    # ------------------------------------------------------

    op.add_column(
        "request_logs",
        sa.Column(
            "endpoint",
            sa.String(),
            nullable=False,
            server_default="/risk/score"
        )
    )

    # ------------------------------------------------------
    # Remove temporary default
    # ------------------------------------------------------

    op.alter_column(
        "request_logs",
        "endpoint",
        server_default=None
    )


# ==========================================================
# DOWNGRADE
# ==========================================================

def downgrade() -> None:
    """
    Remove endpoint tracking.
    """

    op.drop_column(
        "request_logs",
        "endpoint"
    )