from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.auth import get_current_user

from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.models.plan import Plan

router = APIRouter()


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
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

    # Normalize response state (single truth rule)
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

        # 🧠 PLAN SYSTEM (now derived from subscription engine)
        "plan": plan.name if plan else "FREE",
        "plan_id": user.plan_id,

        # 💳 STRIPE IDENTITY
        "stripe_customer_id": getattr(user, "stripe_customer_id", None),

        # ============================
        # 🧠 DAY 3 PHASE 2 ADDITION
        # SINGLE SOURCE OF TRUTH STATE
        # ============================

        "subscription": {
            # CORE STATE ENGINE (IMPORTANT)
            "status": subscription_status,   # active / trialing / past_due / canceled

            # PLAN VIEW (derived from subscription record)
            "current_plan": current_plan,

            # STRIPE LINKAGE
            "stripe_subscription_id": stripe_subscription_id,

            # BILLING TIMING
            "current_period_end": current_period_end,

            # DERIVED FLAG (useful for frontend)
            "is_active": subscription_status == "active"
        }
    }