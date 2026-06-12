from sqlalchemy.orm import Session
from app.models.user import User
from app.models.subscription import Subscription


# ============================================================
# SINGLE SOURCE OF TRUTH: SUBSCRIPTION STATE ENGINE
# ============================================================

VALID_STATES = {
    "active",
    "trialing",
    "past_due",
    "canceled",
    "unpaid"
}


def normalize_status(stripe_status: str) -> str:
    """
    Convert Stripe status into internal canonical state.
    """

    mapping = {
        "active": "active",
        "trialing": "trialing",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "unpaid",
        "incomplete": "past_due",
        "incomplete_expired": "canceled"
    }

    return mapping.get(stripe_status, "past_due")


# ============================================================
# GET CURRENT BILLING STATE (MAIN READ FUNCTION)
# ============================================================

def get_billing_state(db: Session, user: User):
    """
    Single source of truth for billing state.
    """

    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.id.desc())
        .first()
    )

    if not sub:
        return {
            "status": "free",
            "plan": "free",
            "active": False
        }

    return {
        "status": sub.status,
        "plan": sub.current_plan,
        "active": sub.status in ["active", "trialing"]
    }


# ============================================================
# UPDATE SUBSCRIPTION STATE (USED BY WEBHOOKS)
# ============================================================

def upsert_subscription(
    db: Session,
    user_id: int,
    stripe_subscription_id: str,
    status: str,
    plan: str = "PRO",
    period_end=None
):
    """
    Create or update subscription safely.
    """

    normalized_status = normalize_status(status)

    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
        .first()
    )

    if sub:
        sub.status = normalized_status
        sub.current_plan = plan
        sub.current_period_end = period_end
    else:
        sub = Subscription(
            user_id=user_id,
            stripe_subscription_id=stripe_subscription_id,
            status=normalized_status,
            current_plan=plan,
            current_period_end=period_end
        )
        db.add(sub)

    db.commit()
    db.refresh(sub)

    return sub