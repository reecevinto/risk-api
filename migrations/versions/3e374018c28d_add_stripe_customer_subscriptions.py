"""add stripe customer + subscriptions

Revision ID: 3e374018c28d
Revises: f5ad6b3feb9b
Create Date: 2026-06-11 07:11:22.352837

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e374018c28d'
down_revision: Union[str, Sequence[str], None] = 'f5ad6b3feb9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # =========================================
    # 1. CREATE SUBSCRIPTIONS TABLE
    # =========================================
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default="active"),
        sa.Column('current_plan', sa.String(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name="fk_subscriptions_user_id"
        ),

        sa.UniqueConstraint(
            'stripe_subscription_id',
            name="uq_subscriptions_stripe_subscription_id"
        )
    )

    # index for performance (VERY IMPORTANT for SaaS)
    op.create_index(
        "ix_subscriptions_user_id",
        "subscriptions",
        ["user_id"]
    )

    # =========================================
    # 2. ADD STRIPE CUSTOMER ID TO USERS
    # =========================================
    op.add_column(
        'users',
        sa.Column('stripe_customer_id', sa.String(), nullable=True)
    )

    op.create_unique_constraint(
        "uq_users_stripe_customer_id",
        'users',
        ['stripe_customer_id']
    )


def downgrade() -> None:

    # =========================================
    # 1. REMOVE USERS STRIPE FIELD
    # =========================================
    op.drop_constraint(
        "uq_users_stripe_customer_id",
        "users",
        type_="unique"
    )

    op.drop_column('users', 'stripe_customer_id')

    # =========================================
    # 2. DROP SUBSCRIPTIONS TABLE
    # =========================================
    op.drop_index(
        "ix_subscriptions_user_id",
        table_name="subscriptions"
    )

    op.drop_table('subscriptions')