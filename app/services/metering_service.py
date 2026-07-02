from datetime import datetime
from calendar import monthrange

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.subscription import Subscription

from app.core.subscription_states import (
    ACTIVE,
    TRIALING
)

# ============================================================
# DAY 5 PHASE 2
# BILLING CYCLE ENGINE
# ============================================================
from app.services.billing_cycle_service import (
    check_billing_cycle
)

# ============================================================
# REDIS
# ============================================================
from app.core.redis import redis_client

# ============================================================
# BILLING CYCLE KEY
# ============================================================

def get_usage_key(user_id: int):
    """
    Usage is tracked per billing month.

    Example:
        usage:15:2026-06
    """

    cycle = datetime.utcnow().strftime("%Y-%m")

    return f"usage:{user_id}:{cycle}"


# ============================================================
# GET CURRENT USAGE
# ============================================================

def get_usage(user_id: int):

    key = get_usage_key(user_id)

    value = redis_client.get(key)

    return int(value or 0)


# ============================================================
# INCREMENT USAGE
# ============================================================

def increment_usage(user_id: int):

    key = get_usage_key(user_id)

    usage = redis_client.incr(key)

    # --------------------------------------------------------
    # Expire automatically at end of billing month
    # (only set expiry when key is first created)
    # --------------------------------------------------------
    if usage == 1:

        now = datetime.utcnow()

        last_day = monthrange(now.year, now.month)[1]

        expiry = datetime(
            year=now.year,
            month=now.month,
            day=last_day,
            hour=23,
            minute=59,
            second=59
        )

        ttl = int((expiry - now).total_seconds())

        if ttl > 0:
            redis_client.expire(key, ttl)

    return usage


# ============================================================
# GET PLAN LIMIT
# ============================================================

def get_plan_limit(user: User):
    """
    Returns the user's monthly request allowance.

    Uses the Plan table instead of hardcoded limits.
    """

    if user.plan:
        return user.plan.request_limit

    return 1000


# ============================================================
# CHECK LIMIT
# ============================================================

def within_limit(user: User):

    usage = get_usage(user.id)

    limit = get_plan_limit(user)

    return usage < limit


# ============================================================
# DAY 6 PHASE 2
# OVERAGE HELPERS
# ============================================================

def is_overage(user: User):
    """
    Returns True once the included plan limit
    has been reached or exceeded.
    """

    usage = get_usage(user.id)

    limit = get_plan_limit(user)

    return usage >= limit


def overage_requests(user: User):
    """
    Returns the number of billable overage requests.

    Example:

        Limit = 1000
        Usage = 1235

        Returns:
            235
    """

    usage = get_usage(user.id)

    limit = get_plan_limit(user)

    return max(usage - limit, 0)


def usage_summary(user: User):
    """
    Returns a complete usage summary for dashboards,
    billing and reporting.
    """

    usage = get_usage(user.id)

    limit = get_plan_limit(user)

    remaining = max(limit - usage, 0)

    percent = 0

    if limit > 0:
        percent = round((usage / limit) * 100, 2)

    overage = max(usage - limit, 0)

    return {
        "usage": usage,
        "limit": limit,
        "remaining": remaining,
        "percent": percent,
        "overage": overage
    }


# ============================================================
# DASHBOARD HELPERS
# ============================================================

def remaining_requests(user: User):

    usage = get_usage(user.id)

    limit = get_plan_limit(user)

    return max(limit - usage, 0)


def usage_percentage(user: User):

    limit = get_plan_limit(user)

    if limit <= 0:
        return 0

    usage = get_usage(user.id)

    return round((usage / limit) * 100, 2)


# ============================================================
# BILLING ACCESS CHECK
# ============================================================

def can_make_request(
    db: Session,
    user: User
):

    latest_sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id
        )
        .order_by(
            Subscription.id.desc()
        )
        .first()
    )

    # ========================================================
    # DAY 5 PHASE 2
    # Automatically reset usage if billing cycle expired
    # ========================================================
    if latest_sub:

        check_billing_cycle(
            db=db,
            subscription=latest_sub,
            user_id=user.id
        )

        if latest_sub.status not in [
            ACTIVE,
            TRIALING
        ]:
            return False

    # ========================================================
    # DAY 6 PHASE 2
    # Overage charging engine
    #
    # If usage is within the included allowance,
    # always allow the request.
    #
    # Once the allowance has been exhausted:
    #
    # • If the plan allows overage AND the user has
    #   enabled overage billing, continue processing.
    #
    # • Otherwise block the request.
    # ========================================================

    if within_limit(user):
        return True

    if (
        user.plan
        and user.plan.allow_overage
        and user.overage_enabled
    ):
        return True

    return False