"""
============================================================
BILLING SERVICE

Purpose
-------
Handles Stripe integration, subscription activations, plan assignments,
and overage cost calculations.

NOTE: Usage tracking and request metering belong strictly to:
      app/services/metering_service.py
============================================================
"""

import os
import logging
from decimal import Decimal
from typing import Optional
import stripe
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.plan import Plan

# Configure standard logger for containerized/Docker environments
logger = logging.getLogger(__name__)

# ============================================================
# STRIPE CONFIGURATION
# ============================================================

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# ============================================================
# OVERAGE COST CALCULATIONS
# ============================================================

def calculate_overage_cost(
    plan: Optional[Plan],
    overage_requests: int
) -> Decimal:
    """
    Calculates the monetary amount owed for overage usage.

    Example:
        Price = $0.002 / request
        Requests = 500
        Total = $1.00
    """
    if (
        not plan
        or not getattr(plan, "allow_overage", False)
        or overage_requests <= 0
    ):
        return Decimal("0.00")

    overage_price = Decimal(str(getattr(plan, "overage_price", 0.0) or "0.00"))
    return overage_price * Decimal(overage_requests)


def user_overage_cost(
    user: User,
    overage_requests: int
) -> Decimal:
    """
    Convenience wrapper to calculate a user's overage bill 
    using their attached Plan model.
    """
    if user.plan is None:
        return Decimal("0.00")

    return calculate_overage_cost(
        user.plan,
        overage_requests
    )


# ============================================================
# CREATE STRIPE CHECKOUT SESSION
# ============================================================

def create_checkout_session(
    db: Session,
    user: User,
    price_id: str
) -> Optional[str]:
    """
    Creates a Stripe Checkout Session for subscription purchase.
    Guarantees that a valid Stripe Customer ID is created and saved
    to PostgreSQL before initiating the checkout flow.
    """
    # 1. Validate environment price configuration
    if not price_id or not price_id.strip():
        logger.error(f"Checkout attempt failed for User ID {user.id}: Price ID is missing or empty.")
        raise ValueError("Stripe price ID is missing or unconfigured.")

    # 2. Ensure user has a Stripe Customer ID stored in PostgreSQL
    customer_id = getattr(user, "stripe_customer_id", None)

    if not customer_id:
        try:
            logger.info(f"Creating new Stripe customer for User ID {user.id} ({user.email})")
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.id)}
            )
            customer_id = customer.id
            
            user.stripe_customer_id = customer_id
            db.commit()
            db.refresh(user)
            logger.info(f"Successfully linked Stripe Customer ID {customer_id} to User ID {user.id}")
        except Exception as e:
            db.rollback()
            logger.exception(f"Failed to create and persist Stripe customer for User ID {user.id}")
            raise e

    # 3. Build Checkout Session payload with explicit customer assignment
    checkout_kwargs = {
        "customer": customer_id,
        "payment_method_types": ["card"],
        "mode": "subscription",
        "line_items": [
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        "success_url": "http://localhost:3000/success",
        "cancel_url": "http://localhost:3000/cancel",
        "client_reference_id": str(user.id),
        "metadata": {
            "user_id": str(user.id)
        },
        "subscription_data": {
            "metadata": {
                "user_id": str(user.id)
            }
        }
    }

    try:
        session = stripe.checkout.Session.create(**checkout_kwargs)
        return session.url
    except Exception:
        logger.exception(f"Failed to create Stripe Checkout session for User ID {user.id}")
        raise


# ============================================================
# SUBSCRIPTION ACTIVATION
# ============================================================

def activate_subscription(
    db: Session,
    user_id: int,
    plan_name_or_id: str
) -> Optional[User]:
    """
    Activates or updates a user's subscription plan.

    Looks up the corresponding Plan model by ID or name and updates 
    the user's foreign key relationship (plan_id). Fails fast if the target
    plan cannot be found.
    """
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        logger.warning(f"Subscription activation failed: User ID {user_id} not found.")
        return None

    identifier = str(plan_name_or_id).strip()

    # Query plan by ID (if numeric) or by plan name
    if identifier.isdigit():
        target_plan = (
            db.query(Plan)
            .filter(Plan.id == int(identifier))
            .first()
        )
    else:
        target_plan = (
            db.query(Plan)
            .filter(Plan.name.ilike(identifier))
            .first()
        )

    # Fail fast if target plan does not exist
    if not target_plan:
        logger.warning(f"Subscription activation failed: Plan '{identifier}' not found.")
        return None

    try:
        user.plan_id = target_plan.id
        user.plan = target_plan

        db.commit()
        db.refresh(user)
        logger.info(f"Successfully activated Plan ID {target_plan.id} for User ID {user.id}")
        return user
    except Exception:
        db.rollback()
        logger.exception(f"Failed to commit subscription activation for User ID {user_id}")
        raise


# ============================================================
# GET USER PLAN
# ============================================================

def get_user_plan(
    db: Session,
    user_id: int
) -> Optional[Plan]:
    """
    Retrieves the user's currently assigned Plan model.
    """
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return None

    return user.plan