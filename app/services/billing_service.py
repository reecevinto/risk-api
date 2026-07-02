import os
import stripe
import redis

from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.plan import Plan

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# ============================================================
# REDIS CLIENT (ADDED)
# ============================================================

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


# ============================================================
# PLAN LIMITS (LEGACY SUPPORT)
# ============================================================

PLAN_LIMITS = {
    "free": 20,
    "pro": 200,
    "enterprise": 10**9
}


# ============================================================
# CHECK USAGE LIMIT (LEGACY)
# ============================================================

def check_usage_limit(user: User) -> bool:
    """
    Legacy Redis-based usage tracking.

    The new billing engine introduced during Phase 2
    uses metering_service.py instead.
    """

    user_id = str(user.id)
    plan = user.plan or "free"

    limit = PLAN_LIMITS.get(plan, 20)

    today = datetime.utcnow().strftime("%Y-%m-%d")

    key = f"usage:{user_id}:{today}"

    current_usage = redis_client.get(key)

    if current_usage is None:

        redis_client.set(
            key,
            1,
            ex=86400
        )

        return True

    current_usage = int(current_usage)

    if current_usage >= limit:
        return False

    redis_client.incr(key)

    return True


# ============================================================
# DAY 6 PHASE 2
# OVERAGE BILLING HELPERS
# ============================================================

def calculate_overage_cost(
    plan: Plan,
    overage_requests: int
) -> Decimal:
    """
    Calculates the amount owed for overage usage.

    Example

        Price = $0.002/request

        Requests = 500

        Total = $1.00
    """

    if (
        not plan
        or not plan.allow_overage
        or overage_requests <= 0
    ):
        return Decimal("0.00")

    return Decimal(plan.overage_price) * Decimal(overage_requests)


def user_overage_cost(
    user: User,
    overage_requests: int
) -> Decimal:
    """
    Convenience wrapper.

    Calculates the user's overage bill
    using their assigned plan.
    """

    if user.plan is None:
        return Decimal("0.00")

    return calculate_overage_cost(
        user.plan,
        overage_requests
    )


# ============================================================
# CREATE CHECKOUT SESSION
# ============================================================

def create_checkout_session(
    user: User,
    price_id: str
):

    session = stripe.checkout.Session.create(

        payment_method_types=["card"],

        mode="subscription",

        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],

        success_url="http://localhost:3000/success",

        cancel_url="http://localhost:3000/cancel",

        metadata={
            "user_id": user.id
        }
    )

    return session.url


# ============================================================
# UPDATE USER PLAN AFTER PAYMENT
# ============================================================

def activate_subscription(
    db: Session,
    user_id: int,
    plan: str
):

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return None

    user.plan = plan

    db.commit()

    return user


# ============================================================
# GET USER PLAN
# ============================================================

def get_user_plan(
    db: Session,
    user_id: int
):

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return None

    return user.plan