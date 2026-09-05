from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.subscription import Subscription
from app.models.request_log import RequestLog

from app.core.subscription_states import (
    ACTIVE,
    TRIALING
)

# ============================================================
# BILLING CYCLE SERVICE
# ============================================================
from app.services.billing_cycle_service import (
    check_billing_cycle
)


# ============================================================
# 1. SUBSCRIPTION & PLAN HELPERS
# ============================================================

def get_current_subscription(db: Session, user: User) -> Optional[Subscription]:
    """
    Fetches the active/latest subscription record for the given user.
    """
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.id.desc())
        .first()
    )


def get_plan_limit(user: User) -> int:
    """
    Returns the user's monthly request allowance based on their attached Plan model.
    Defaults to 1000 if no custom plan limit is defined.
    """
    if user.plan and hasattr(user.plan, "request_limit") and user.plan.request_limit:
        return user.plan.request_limit

    return 1000


# ============================================================
# 2. CENTRALIZED USAGE ENGINE (SINGLE SQL SOURCE OF TRUTH)
# ============================================================

def get_current_usage(db: Session, user: User) -> int:
    """
    SINGLE SOURCE OF TRUTH FOR USAGE ACCOUNTING.

    Queries PostgreSQL `request_logs` within the active subscription's 
    billing window (`current_period_start` to `current_period_end`).

    If no subscription exists or timestamps are missing, falls back to 
    lifetime total request logs for the user.
    """
    subscription = get_current_subscription(db, user)

    query = db.query(func.count(RequestLog.id)).filter(RequestLog.user_id == user.id)

    # Filter by subscription billing window if present
    if subscription:
        if getattr(subscription, "current_period_start", None):
            query = query.filter(RequestLog.created_at >= subscription.current_period_start)
        if getattr(subscription, "current_period_end", None):
            query = query.filter(RequestLog.created_at < subscription.current_period_end)

    count = query.scalar()
    return count or 0


# ============================================================
# 3. METERING & OVERAGE CALCULATION HELPERS
# ============================================================

def within_limit(db: Session, user: User) -> bool:
    """
    Returns True if current billing cycle usage is strictly below the plan limit.
    """
    usage = get_current_usage(db, user)
    limit = get_plan_limit(user)
    return usage < limit


def is_overage(db: Session, user: User) -> bool:
    """
    Returns True once the included plan limit has been reached or exceeded.
    """
    usage = get_current_usage(db, user)
    limit = get_plan_limit(user)
    return usage >= limit


def overage_requests(db: Session, user: User) -> int:
    """
    Returns the exact count of billable requests exceeding the plan limit.
    """
    usage = get_current_usage(db, user)
    limit = get_plan_limit(user)
    return max(usage - limit, 0)


def remaining_requests(db: Session, user: User) -> int:
    """
    Returns remaining requests in the active plan limit (floored at 0).
    """
    usage = get_current_usage(db, user)
    limit = get_plan_limit(user)
    return max(limit - usage, 0)


def usage_percentage(db: Session, user: User) -> float:
    """
    Returns the consumption percentage relative to the plan limit.
    """
    limit = get_plan_limit(user)
    if limit <= 0:
        return 0.0

    usage = get_current_usage(db, user)
    return round((usage / limit) * 100.0, 2)


def usage_summary(db: Session, user: User) -> Dict[str, Any]:
    """
    Returns a unified usage summary dictionary suitable for API responses,
    dashboards, and billing reports.
    """
    usage = get_current_usage(db, user)
    limit = get_plan_limit(user)
    remaining = max(limit - usage, 0)
    percent = round((usage / limit) * 100.0, 2) if limit > 0 else 0.0
    overage = max(usage - limit, 0)

    return {
        "usage": usage,
        "limit": limit,
        "remaining": remaining,
        "percent": percent,
        "overage": overage
    }


# ============================================================
# 4. BILLING ACCESS GATEWAY
# ============================================================

def can_make_request(db: Session, user: User) -> bool:
    """
    Evaluates whether an incoming API request should be processed or blocked.

    1. Checks and updates billing cycle state if expired.
    2. Enforces active/trialing subscription status.
    3. Allows requests if within included limit.
    4. Evaluates plan overage permissions and user overage settings when limit is exceeded.
    """
    latest_sub = get_current_subscription(db, user)

    # --------------------------------------------------------
    # 1. Billing Cycle Reset & Status Validation
    # --------------------------------------------------------
    if latest_sub:
        check_billing_cycle(
        db=db,
        subscription=latest_sub
    )

        if latest_sub.status not in [ACTIVE, TRIALING]:
            return False

    # --------------------------------------------------------
    # 2. Included Allowance Check
    # --------------------------------------------------------
    if within_limit(db, user):
        return True

    # --------------------------------------------------------
    # 3. Overage Engine Evaluation
    # --------------------------------------------------------
    plan_allows_overage = bool(user.plan and getattr(user.plan, "allow_overage", False))
    user_enabled_overage = bool(getattr(user, "overage_enabled", False))

    if plan_allows_overage and user_enabled_overage:
        return True

    return False