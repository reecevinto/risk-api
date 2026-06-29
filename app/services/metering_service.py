import os
import redis

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
# REDIS
# ============================================================

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# ============================================================
# PLAN LIMITS
# ============================================================

PLAN_LIMITS = {
    1: 1000,          # FREE
    2: 100000,        # PRO
    3: 1000000        # ENTERPRISE
}

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

    return PLAN_LIMITS.get(
        user.plan_id,
        PLAN_LIMITS[1]
    )


# ============================================================
# CHECK LIMIT
# ============================================================

def within_limit(user: User):

    usage = get_usage(user.id)

    limit = get_plan_limit(user)

    return usage < limit


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

    if latest_sub:

        if latest_sub.status not in [
            ACTIVE,
            TRIALING
        ]:
            return False

    return within_limit(user)