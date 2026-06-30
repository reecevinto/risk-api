from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.core.redis import redis_client

# ============================================================
# DAY 5 PHASE 2
# BILLING CYCLE ENGINE
# ============================================================


def needs_reset(subscription: Subscription) -> bool:
    """
    Returns True when the current billing period has ended.
    """

    if not subscription:
        return False

    if not subscription.current_period_end:
        return False

    return datetime.utcnow() >= subscription.current_period_end


# ============================================================
# RESET REDIS USAGE
# ============================================================

def reset_usage(user_id: int):
    """
    Clears the Redis usage counter for the user's
    current billing cycle.
    """

    cycle = datetime.utcnow().strftime("%Y-%m")

    key = f"usage:{user_id}:{cycle}"

    redis_client.set(key, 0)


# ============================================================
# ADVANCE BILLING PERIOD
# ============================================================

def advance_billing_period(
    db: Session,
    subscription: Subscription
):
    """
    Advances the billing period by one month.

    NOTE:
    During development we advance locally.
    Once Stripe Billing is fully enabled,
    Stripe webhooks will become the source of truth.
    """

    now = datetime.utcnow()

    subscription.current_period_start = now
    subscription.current_period_end = now + timedelta(days=30)

    db.commit()
    db.refresh(subscription)


# ============================================================
# MAIN BILLING CYCLE CHECK
# ============================================================

def check_billing_cycle(
    db: Session,
    subscription: Subscription,
    user_id: int
):
    """
    Automatically resets usage when the billing
    period has expired.
    """

    if not subscription:
        return

    if needs_reset(subscription):

        reset_usage(user_id)

        advance_billing_period(
            db,
            subscription
        )

# ============================================================
# BILLING PERIOD HELPERS
# ============================================================

def get_current_billing_period(subscription: Subscription):
    """
    Returns the current billing period.
    """

    if not subscription:
        return None

    return {
        "start": subscription.current_period_start,
        "end": subscription.current_period_end
    }


def get_next_reset_date(subscription: Subscription):
    """
    Returns when usage will reset.
    """

    if not subscription:
        return None

    return subscription.current_period_end