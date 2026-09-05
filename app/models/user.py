"""
============================================================
USER MODEL
============================================================

Core application user model.

Responsibilities
----------------
✓ Store authenticated user identity
✓ Store billing-plan association
✓ Store Stripe customer association
✓ Store overage-billing configuration
✓ Maintain API-key relationship
✓ Maintain subscription relationship

IMPORTANT
---------
This model is intentionally kept schema-compatible with the
current Alembic migration history.

Current migration HEAD:

    903267aa7fb0
    Add subscription current period start

No new database columns or constraints are introduced here.
============================================================
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
)

from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """
    Application user.

    A User may have:

        • API keys
        • A billing plan
        • One or more subscriptions
        • Stripe customer mapping
        • Overage billing configuration

    DeviceFingerprint and RequestLog records reference this
    user's primary key through user_id.
    """

    __tablename__ = "users"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # USER IDENTITY
    # ========================================================

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    name = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    # ========================================================
    # BILLING PLAN
    # ========================================================

    # Current billing plan associated with this user.

    plan_id = Column(
        Integer,
        ForeignKey("plans.id"),
    )

    # ========================================================
    # STRIPE CUSTOMER
    # ========================================================

    # Maps this application user to the corresponding
    # Stripe customer.

    stripe_customer_id = Column(
        String,
        unique=True,
        nullable=True,
    )

    # ========================================================
    # DAY 6 PHASE 2
    # OVERAGE BILLING
    # ========================================================

    # Whether this customer has overage billing enabled.

    overage_enabled = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    # API keys belonging to this user.

    api_keys = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Current billing plan.

    plan = relationship(
        "Plan",
    )

    # Subscriptions belonging to this user.

    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )