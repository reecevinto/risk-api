from sqlalchemy.orm import Session

from app.models.request_log import RequestLog


def log_request(
    db: Session,
    user_id: int,
    email: str,
    phone: str,
    ip: str,
    risk: dict,
    is_overage: bool = False
):
    """
    Persist a completed API request.

    Day 6 Phase 2
    -------------
    Requests are now tagged as either:

        • Normal request
        • Overage request

    This allows future billing reconciliation,
    analytics and invoice generation.
    """

    log = RequestLog(

        user_id=user_id,

        email=email,

        phone=phone,

        ip=ip,

        risk_score=risk.get("risk_score"),

        trust_level=risk.get("trust_level"),

        flags=risk.get("flags"),

        # ==========================================
        # DAY 6 PHASE 2
        # Overage tracking
        # ==========================================
        is_overage=is_overage

    )

    db.add(log)

    db.commit()

    db.refresh(log)

    return log