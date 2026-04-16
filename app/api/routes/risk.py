from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.auth import get_current_user

from app.schemas.risky import RiskRequest

from app.services.phone_service import analyze_phone
from app.services.email_service import analyze_email
from app.services.ip_service import analyze_ip
from app.services.risk_engine import compute_risk

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
# 🔥 DAY 8 — MAIN PRODUCT ENDPOINT
# ============================================================
@router.post("/score")
def score_risk(
    payload: RiskRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    phone_data = analyze_phone(payload.phone) if payload.phone else None
    email_data = analyze_email(payload.email) if payload.email else None
    ip_data = analyze_ip(payload.ip) if payload.ip else None

    risk = compute_risk(
        phone_data=phone_data,
        email_data=email_data,
        ip_data=ip_data
    )

    return {
        "input": payload.dict(),
        "phone_analysis": phone_data,
        "email_analysis": email_data,
        "ip_analysis": ip_data,
        "risk_analysis": risk,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }