from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.auth import get_current_user

# from app.models import subscription 

from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.models.plan import Plan

# ============================================================
# DAY 4 PHASE 2 — METERED BILLING ENGINE
# ============================================================
from app.services.metering_service import usage_summary

# ============================================================
# DAY 6 PHASE 2 — OVERAGE ENGINE
# ============================================================

from app.services.overage_service import (
    calculate_overage_charge
)


# Day 5 Phase 2 — Billing Cycle Reset
from app.services.billing_cycle_service import (
    get_current_billing_period,
    get_next_reset_date
)

router = APIRouter()


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # 🔥 get latest API key for this user
    api_key = db.query(APIKey)\
        .filter(APIKey.user_id == user.id)\
        .order_by(APIKey.id.desc())\
        .first()

    # ============================
    # 🧠 DAY 1 PHASE 2 ADDITIONS
    # ============================

    # 🔥 get plan (FREE / PRO / ENTERPRISE)
    plan = None

    if user.plan_id:
        plan = db.query(Plan)\
            .filter(Plan.id == user.plan_id)\
            .first()

    # 🔥 get latest subscription (Stripe lifecycle)
    # 👉 DAY 3 UPDATE: this is now SOURCE OF TRUTH (state engine)
    subscription = db.query(Subscription)\
        .filter(Subscription.user_id == user.id)\
        .order_by(Subscription.id.desc())\
        .first()

    # ============================
    # 🧠 DAY 3 PHASE 2 ADDITION
    # SUBSCRIPTION STATE ENGINE
    # ============================

    if subscription:
        subscription_status = subscription.status
        current_plan = subscription.current_plan
        stripe_subscription_id = subscription.stripe_subscription_id
        current_period_end = subscription.current_period_end
    else:
        subscription_status = "none"
        current_plan = "FREE"
        stripe_subscription_id = None
        current_period_end = None

    # ============================
    # 🧠 DAY 4 PHASE 2 ADDITION
    # METERED BILLING ENGINE
    # ============================

    # current_usage = get_usage(user.id)
    # usage_limit = get_plan_limit(user)

    # ============================
    # DAY 5 PHASE 2
    # BILLING CYCLE
    # ============================

    billing_period = get_current_billing_period(subscription)
    next_reset = get_next_reset_date(subscription)

    # ============================
    # DAY 6 PHASE 2
    # OVERAGE BILLING
    # ============================

    usage = usage_summary(user)

    overage = calculate_overage_charge(user)

    # ============================
    # RESPONSE (ENHANCED)
    # ============================
    return {
        "id": user.id,
        "email": user.email,

        # existing (UNCHANGED)
        "api_key": api_key.key if api_key else None,

        # ============================
        # DAY 1 PHASE 2 ADDITIONS
        # ============================

        # 🧠 PLAN SYSTEM
        "plan": plan.name if plan else "FREE",
        "plan_id": user.plan_id,

        # 💳 STRIPE IDENTITY
        "stripe_customer_id": getattr(
            user,
            "stripe_customer_id",
            None
        ),

        # ============================
        # 🧠 DAY 3 PHASE 2 ADDITION
        # SINGLE SOURCE OF TRUTH STATE
        # ============================

        "subscription": {
            # CORE STATE ENGINE
            "status": subscription_status,

            # PLAN VIEW
            "current_plan": current_plan,

            # STRIPE LINKAGE
            "stripe_subscription_id": stripe_subscription_id,

            # BILLING TIMING
            "current_period_end": current_period_end,

            # DERIVED FLAG
            "is_active": subscription_status in [
                "active",
                "trialing"
            ]
        },

       # ============================
# DAY 4 PHASE 2
# METERED BILLING
# ============================

"usage": {

    "current": usage["usage"],

    "limit": usage["limit"],

    "remaining": usage["remaining"],

    "percent_used": usage["percent"]

},

# ============================
# DAY 5 PHASE 2
# BILLING CYCLE
# ============================

"billing_cycle": {
    "current_period": billing_period,
    "next_reset": next_reset
},

# ============================
# DAY 6 PHASE 2
# OVERAGE SETTINGS
# ============================

"overage_enabled": user.overage_enabled,

    "plan_allow_overage": (
        plan.allow_overage
        if plan
        else False
    ),

    "billing": {

        "overage_requests": overage["overage_requests"],
        "price_per_request": overage["price_per_request"],
        "total_charge": overage["total_charge"],
        "is_overage": overage["overage_requests"] > 0
}
    }