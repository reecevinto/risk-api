# app/api/routes/admin.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.request_log import RequestLog
from app.api.routes.auth import get_current_user
from sqlalchemy import func

router = APIRouter()

@router.get("/usage")
def get_usage(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    total_requests = db.query(RequestLog)\
        .filter(RequestLog.user_id == user.id)\
        .count()

    avg_risk = db.query(func.avg(RequestLog.risk_score))\
        .filter(RequestLog.user_id == user.id)\
        .scalar()

    recent = db.query(RequestLog)\
        .filter(RequestLog.user_id == user.id)\
        .order_by(RequestLog.created_at.desc())\
        .limit(5)\
        .all()

    return {
        "total_requests": total_requests,
        "average_risk_score": float(avg_risk or 0),
        "recent_requests": [
            {
                "ip": r.ip,
                "email": r.email,
                "phone": r.phone,
                "risk_score": r.risk_score,
                "time": r.created_at
            }
            for r in recent
        ]
    }