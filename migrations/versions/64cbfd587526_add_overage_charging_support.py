"""add overage charging support

Revision ID: 64cbfd587526
Revises: 3e374018c28d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "64cbfd587526"
down_revision = "3e374018c28d"
branch_labels = None
depends_on = None


def upgrade():

    # =====================================================
    # Plans
    # =====================================================

    op.add_column(
        "plans",
        sa.Column(
            "allow_overage",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )

    op.add_column(
        "plans",
        sa.Column(
            "overage_price",
            sa.Numeric(10, 4),
            nullable=False,
            server_default="0"
        )
    )

    # =====================================================
    # Users
    # =====================================================

    op.add_column(
        "users",
        sa.Column(
            "overage_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )

    # =====================================================
    # Request Logs
    # =====================================================

    op.add_column(
        "request_logs",
        sa.Column(
            "is_overage",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )

    # =====================================================
    # Remove temporary defaults
    # =====================================================

    op.alter_column(
        "plans",
        "allow_overage",
        server_default=None
    )

    op.alter_column(
        "plans",
        "overage_price",
        server_default=None
    )

    op.alter_column(
        "users",
        "overage_enabled",
        server_default=None
    )

    op.alter_column(
        "request_logs",
        "is_overage",
        server_default=None
    )


def downgrade():

    op.drop_column("request_logs", "is_overage")

    op.drop_column("users", "overage_enabled")

    op.drop_column("plans", "overage_price")

    op.drop_column("plans", "allow_overage")