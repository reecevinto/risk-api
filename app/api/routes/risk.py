from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.auth import get_current_user

from app.models import user
from app.schemas.risky import RiskRequest

from app.services.phone_service import analyze_phone
from app.services.email_service import analyze_email
from app.services.ip_service import analyze_ip
from app.services.risk_engine import compute_risk
from app.services.log_service import log_request
from app.services.rate_limiter import check_rate_limit
from app.services.billing_service import check_usage_limit

# 🔥 DAY 14 ADDITION (Stripe placeholder integration)
from app.services.billing_service import get_user_plan

router = APIRouter()


# ============================================================
# 🔹 EXISTING TEST ENDPOINT (KEEP THIS)
# ============================================================
@router.get("/analyze")
def analyze_risk(
    phone: str = None,
    email: str = None,
    ip: str = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    phone_data = analyze_phone(phone) if phone else None
    email_data = analyze_email(email) if email else None
    ip_data = analyze_ip(ip) if ip else None

    risk = compute_risk(
        phone_data=phone_data,
        email_data=email_data,
        ip_data=ip_data
    )

    return {
        "input": {
            "phone": phone,
            "email": email,
            "ip": ip
        },
        "risk_analysis": risk,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }


# ============================================================
# 🔥 MAIN PRODUCTION ENDPOINT (DAY 14 ENHANCED)
# ============================================================
@router.post("/score")
def score_risk(
    payload: RiskRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):

    # ========================================================
    # 🔥 STEP 0 — GET USER PLAN (DAY 14 ADDITION)
    # ========================================================
    plan = get_user_plan(db, user)

    if not plan:
        raise HTTPException(
            status_code=403,
            detail="No active plan found. Please subscribe."
        )

    # ========================================================
    # 🔥 STEP 1 — USAGE LIMIT CHECK (BILLING CORE)
    # ========================================================
    if not check_usage_limit(db, user):
        raise HTTPException(
            status_code=403,
            detail="Monthly usage limit exceeded. Upgrade your plan."
        )

    # ========================================================
    # 🔥 STEP 2 — RATE LIMIT CHECK
    # ========================================================
    if not check_rate_limit(user.id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )

    # ========================================================
    # 🔥 STEP 3 — ANALYZE INPUTS
    # ========================================================
    phone_data = analyze_phone(payload.phone) if payload.phone else None
    email_data = analyze_email(payload.email) if payload.email else None
    ip_data = analyze_ip(payload.ip) if payload.ip else None

    # ========================================================
    # 🔥 STEP 4 — COMPUTE RISK ENGINE
    # ========================================================
    risk = compute_risk(
        phone_data=phone_data,
        email_data=email_data,
        ip_data=ip_data
    )

    # ========================================================
    # 🔥 STEP 5 — LOG REQUEST (BILLING TRACKING CRITICAL)
    # ========================================================
    log_request(
        db=db,
        user_id=user.id,
        email=payload.email,
        phone=payload.phone,
        ip=payload.ip,
        risk=risk
    )

    # ========================================================
    # 🔥 STEP 6 — RESPONSE (NOW BILLING-AWARE)
    # ========================================================
    return {
        "input": payload.dict(),

        # intelligence layers
        "phone_analysis": phone_data,
        "email_analysis": email_data,
        "ip_analysis": ip_data,
        "risk_analysis": risk,

        # 🔥 DAY 14 ADDITION
        "billing": {
            "plan": plan.name,
            "request_limit": plan.request_limit
        },

        "user": {
            "id": user.id,
            "email": user.email
        }
    }