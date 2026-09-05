"""
============================================================
PLAN MODEL
============================================================

Purpose
-------
Defines the billing plans available to application users.

Responsibilities
----------------
✓ Store plan identity
✓ Store request usage limits
✓ Store whether overage billing is permitted
✓ Store the price charged for overage requests

IMPORTANT
---------
This model is part of the existing billing/metering system.

The current schema is intentionally preserved.

No new columns, constraints, indexes, or relationships are
introduced in this stage.

Current billing fields:

    id
    name
    request_limit
    allow_overage
    overage_price
============================================================
"""

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Numeric,
)

from app.db.base import Base


class Plan(Base):
    """
    Billing plan configuration.

    A User references the current plan through:

        User.plan_id -> Plan.id

    The metering and overage services use this model to
    determine request limits and overage pricing.
    """

    __tablename__ = "plans"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # PLAN IDENTITY
    # ========================================================

    name = Column(
        String,
        unique=True,
    )

    # ========================================================
    # REQUEST LIMIT
    # ========================================================

    # Maximum number of requests included in the plan's
    # normal usage allowance.

    request_limit = Column(
        Integer,
    )

    # ========================================================
    # DAY 6 PHASE 2
    # OVERAGE SETTINGS
    # ========================================================

    # Whether requests beyond the normal plan limit may be
    # billed as overage requests.

    allow_overage = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Price charged for each overage request.

    overage_price = Column(
        Numeric(10, 4),
        nullable=False,
        default=0,
    )