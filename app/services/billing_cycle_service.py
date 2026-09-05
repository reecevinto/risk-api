from datetime import datetime
from typing import Optional, Dict
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models.subscription import Subscription

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
# ADVANCE BILLING PERIOD
# ============================================================

def advance_billing_period(
    db: Session,
    subscription: Subscription
):
    """
    Advances the billing period by one calendar month using relativedelta.

    NOTE:
    During local development or non-Stripe flows, we advance period bounds in 
    PostgreSQL. Because metering dynamically queries request_logs between 
    current_period_start and current_period_end, updating these timestamps 
    automatically resets active billing cycle usage.
    
    Once Stripe Billing is fully active, Stripe webhooks become the external 
    source of truth for updating these subscription boundaries.
    """

    now = datetime.utcnow()

    subscription.current_period_start = now
    subscription.current_period_end = now + relativedelta(months=1)

    # db.flush()
    db.commit()
    db.refresh(subscription)


# ============================================================
# MAIN BILLING CYCLE CHECK
# ============================================================

def check_billing_cycle(
    db: Session,
    subscription: Subscription
):
    """
    Automatically advances the subscription billing window.

    Because metering queries request_logs using the active billing period boundaries, 
    advancing the billing window automatically begins a new usage cycle without 
    resetting or deleting any historical data.
    """

    if not subscription:
        return

    if subscription and needs_reset(subscription):
        advance_billing_period(db, subscription)


# ============================================================
# BILLING PERIOD HELPERS
# ============================================================

def get_current_billing_period(subscription: Subscription) -> Optional[Dict[str, Optional[datetime]]]:
    """
    Returns the current billing period dictionary containing start and end timestamps.
    """

    if not subscription:
        return None

    return {
        "start": subscription.current_period_start,
        "end": subscription.current_period_end
    }


def get_next_reset_date(subscription: Subscription) -> Optional[datetime]:
    """
    Returns the exact timestamp when usage will next reset.
    """

    if not subscription:
        return None

    return subscription.current_period_end