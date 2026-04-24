from sqlalchemy.orm import Session
from app.models.request_log import RequestLog


def log_request(
    db: Session,
    user_id: int,
    email: str,
    phone: str,
    ip: str,
    risk: dict
):
    log = RequestLog(
        user_id=user_id,
        email=email,
        phone=phone,
        ip=ip,
        risk_score=risk.get("risk_score"),
        trust_level=risk.get("trust_level"),
        flags=risk.get("flags")
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log