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

# ============================================================
# DAY 4 PHASE 2 — METERED BILLING ENGINE
# ============================================================
from app.services.metering_service import (
    can_make_request,
    increment_usage,
    get_usage,
    get_plan_limit
)

# ============================================================
# DAY 5 PHASE 2 — BILLING CYCLE RESET
# ============================================================


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
    user=Depends(get_current_user)
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
# 🔥 MAIN PRODUCTION ENDPOINT
# ============================================================
@router.post("/score")
def score_risk(
    payload: RiskRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    # ========================================================
    # DAY 5 PHASE 2
    # ENSURE BILLING CYCLE IS CURRENT
    # ========================================================
  
    # ========================================================
    # STEP 0 — BILLING STATE CHECK
    # ========================================================
    if not can_make_request(db, user):
        raise HTTPException(
            status_code=403,
            detail="Usage limit exceeded or subscription inactive."
        )

    # ========================================================
    # STEP 1 — RATE LIMIT CHECK
    # ========================================================
    if not check_rate_limit(user.id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )

    # ========================================================
    # STEP 2 — ANALYZE INPUTS
    # ========================================================
    phone_data = analyze_phone(payload.phone) if payload.phone else None
    email_data = analyze_email(payload.email) if payload.email else None
    ip_data = analyze_ip(payload.ip) if payload.ip else None

    # ========================================================
    # STEP 3 — COMPUTE RISK ENGINE
    # ========================================================
    risk = compute_risk(
        phone_data=phone_data,
        email_data=email_data,
        ip_data=ip_data
    )

    # ========================================================
    # STEP 4 — LOG REQUEST
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
    # STEP 5 — METERED BILLING
    # ========================================================
    increment_usage(user.id)

    current_usage = get_usage(user.id)
    usage_limit = get_plan_limit(user)

    # ========================================================
    # STEP 6 — RESPONSE
    # ========================================================
    return {
        "input": payload.dict(),

        "phone_analysis": phone_data,
        "email_analysis": email_data,
        "ip_analysis": ip_data,
        "risk_analysis": risk,

        "billing": {
            "plan_id": user.plan_id,
            "usage": current_usage,
            "usage_limit": usage_limit,
            "remaining": max(
                0,
                usage_limit - current_usage
            )
        },

        "user": {
            "id": user.id,
            "email": user.email
        }
    }