from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.api.routes.auth import get_current_user

from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.request_log import RequestLog  # Ensure RequestLog import path matches your project structure

# ============================================================
# METERED BILLING & OVERAGE ENGINES
# ============================================================
from app.services.metering_service import usage_summary
from app.services.overage_service import calculate_overage_charge
from app.services.billing_cycle_service import (
    get_current_billing_period,
    get_next_reset_date
)

# ============================================================
# DEVICE INTELLIGENCE ENGINE
# ============================================================
from app.services.device_intelligence import DeviceIntelligenceService

router = APIRouter()


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # 1. Fetch latest API key
    api_key_obj = db.query(APIKey)\
        .filter(APIKey.user_id == user.id)\
        .order_by(APIKey.id.desc())\
        .first()

    api_key_str = api_key_obj.key if api_key_obj else getattr(user, "api_key", None)
    key_last_rotated = getattr(api_key_obj, "created_at", None) or getattr(user, "key_last_rotated", None)

    # 2. Fetch Plan
    plan = None
    if user.plan_id:
        plan = db.query(Plan)\
            .filter(Plan.id == user.plan_id)\
            .first()

    plan_name = plan.name if plan else getattr(user, "plan_type", "FREE")
    request_limit = plan.request_limit if (plan and plan.request_limit) else getattr(user, "request_limit", 1000)
    plan_allow_overage = plan.allow_overage if (plan and hasattr(plan, "allow_overage")) else getattr(user, "plan_allows_overage", False)

    # 3. Fetch Subscription (Source of Truth for billing timing)
    subscription = db.query(Subscription)\
        .filter(Subscription.user_id == user.id)\
        .order_by(Subscription.id.desc())\
        .first()

    if subscription:
        subscription_status = subscription.status
        current_plan = subscription.current_plan
        stripe_subscription_id = subscription.stripe_subscription_id
        current_period_end = subscription.current_period_end
        current_period_start = getattr(subscription, "current_period_start", None)
    else:
        subscription_status = getattr(user, "subscription_status", "ACTIVE")
        current_plan = plan_name
        stripe_subscription_id = None
        current_period_start = getattr(user, "period_start", None)
        current_period_end = getattr(user, "period_end", None)

    # 4. SQL Analytics Aggregation (Total requests & Risk score)
    total_requests_sql = db.query(func.count(RequestLog.id))\
        .filter(RequestLog.user_id == user.id)\
        .scalar() or 0

    avg_risk_sql = db.query(func.avg(RequestLog.risk_score))\
        .filter(RequestLog.user_id == user.id)\
        .scalar() or 0.0

    # 5. Billing Cycle & Overage Services
    billing_period = get_current_billing_period(subscription)
    next_reset = get_next_reset_date(subscription)

    # Pass `db` as the first positional argument
    usage = usage_summary(db, user)
    overage = calculate_overage_charge(db, user)

    # Calculate percentages for dashboard cards
    total_requests = total_requests_sql if total_requests_sql > 0 else usage.get("usage", 0)
    limit = request_limit if request_limit > 0 else 1000
    usage_percentage = min((total_requests / limit) * 100.0, 100.0)

    overage_reqs = overage.get("overage_requests", 0)
    overage_price = overage.get("price_per_request", 0.0)
    overage_charge = overage.get("total_charge", 0.0)
    overage_percentage = (overage_reqs / limit) * 100.0 if limit > 0 else 0.0

    # 6. Device Intelligence
    device_summary = DeviceIntelligenceService.get_dashboard_summary(db, user.id)
    known_devices = DeviceIntelligenceService.get_known_devices(db, user.id)
    current_device = DeviceIntelligenceService.get_current_device(db, user.id)
    device_timeline = DeviceIntelligenceService.get_device_timeline(db, user.id)
    device_health = DeviceIntelligenceService.get_device_health(db, user.id)

    # 7. Unified Response Payload (Flattens top-level keys for dashboard.js while retaining nested keys)
    return {
        # --- Core Identity ---
        "id": user.id,
        "email": user.email,
        "api_key": api_key_str,
        "key_last_rotated": key_last_rotated,

        # --- Top KPIs Expected by dashboard.js ---
        "total_requests": total_requests,
        "request_limit": limit,
        "usage_percentage": usage_percentage,
        "average_risk_score": float(avg_risk_sql),
        "plan_type": plan_name,
        "plan_id": user.plan_id,

        # --- Billing & Overage Expected by dashboard.js ---
        "subscription_status": subscription_status,
        "stripe_customer_id": getattr(user, "stripe_customer_id", None),
        "overage_enabled": getattr(user, "overage_enabled", False),
        "overage_charge": overage_charge,
        "overage_requests": overage_reqs,
        "overage_price": overage_price,
        "overage_percentage": overage_percentage,
        "plan_allows_overage": plan_allow_overage,
        "period_start": current_period_start,
        "period_end": current_period_end or next_reset,

        # --- Backward-Compatible Nested Structures ---
        "plan": plan_name,
        "subscription": {
            "status": subscription_status,
            "current_plan": current_plan,
            "stripe_subscription_id": stripe_subscription_id,
            "current_period_end": current_period_end,
            "is_active": subscription_status.lower() in ["active", "trialing"]
        },
        "usage": {
            "current": total_requests,
            "limit": limit,
            "remaining": max(limit - total_requests, 0),
            "percent_used": usage_percentage
        },
        "billing_cycle": {
            "current_period": billing_period,
            "next_reset": next_reset
        },
        "billing": {
            "overage_requests": overage_reqs,
            "price_per_request": overage_price,
            "total_charge": overage_charge,
            "is_overage": overage_reqs > 0
        },
        "device_intelligence": {
            "summary": device_summary,
            "known_devices": known_devices,
            "current_device": current_device,
            "timeline": device_timeline,
            "health": device_health
        }
    }