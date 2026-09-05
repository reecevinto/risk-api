from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.auth import get_current_user
from app.models.request_log import RequestLog

router = APIRouter()


# ============================================================
# RESPONSE SCHEMAS
# ============================================================

class DailyUsage(BaseModel):
    date: str
    requests: int


class EndpointBreakdown(BaseModel):
    endpoint: str
    requests: int


class EndpointRisk(BaseModel):
    endpoint: str
    average_risk: float


class RecentRequest(BaseModel):
    timestamp: str
    endpoint: str
    email: str | None = None
    ip_address: str | None = None
    risk_score: float
    is_overage: bool


class AnalyticsSummaryResponse(BaseModel):
    requests_today: int
    requests_this_week: int
    most_used_endpoint: str
    most_used_endpoint_risk: float
    daily_usage: list[DailyUsage]
    endpoint_breakdown: list[EndpointBreakdown]
    endpoint_average_risk: list[EndpointRisk]
    recent_requests: list[RecentRequest]


# ============================================================
# ANALYTICS SUMMARY
# ============================================================

@router.get("/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    now = datetime.utcnow()

    today_start = datetime.combine(
        now.date(),
        datetime.min.time()
    )

    week_start = now - timedelta(days=7)

    # ========================================================
    # TODAY
    # ========================================================

    requests_today = db.query(RequestLog).filter(
        RequestLog.user_id == user.id,
        RequestLog.created_at >= today_start
    ).count()

    # ========================================================
    # LAST 7 DAYS
    # ========================================================

    requests_this_week = db.query(RequestLog).filter(
        RequestLog.user_id == user.id,
        RequestLog.created_at >= week_start
    ).count()

    # ========================================================
    # MOST USED ENDPOINT
    # ========================================================

    endpoint_stats = (
        db.query(
            RequestLog.endpoint,
            func.count(RequestLog.id).label("count"),
            func.avg(RequestLog.risk_score).label("avg_risk")
        )
        .filter(RequestLog.user_id == user.id)
        .group_by(RequestLog.endpoint)
        .order_by(func.count(RequestLog.id).desc())
        .all()
    )

    if endpoint_stats:
        most_used_endpoint = endpoint_stats[0].endpoint
        most_used_endpoint_risk = round(
            float(endpoint_stats[0].avg_risk),
            2
        )
    else:
        most_used_endpoint = "--"
        most_used_endpoint_risk = 0.0

    # ========================================================
    # DAILY USAGE
    # ========================================================

    last_14_days = now - timedelta(days=14)

    daily_usage_query = (
        db.query(
            func.date(RequestLog.created_at).label("day"),
            func.count(RequestLog.id)
        )
        .filter(
            RequestLog.user_id == user.id,
            RequestLog.created_at >= last_14_days
        )
        .group_by(func.date(RequestLog.created_at))
        .order_by(func.date(RequestLog.created_at))
        .all()
    )
    daily_usage = [
        {
            "date": str(day),
            "requests": count
        }
        for day, count in daily_usage_query
    ]

    # ========================================================
    # ENDPOINT BREAKDOWN
    # ========================================================

    endpoint_breakdown = [
        {
            "endpoint": row.endpoint,
            "requests": row.count
        }
        for row in endpoint_stats
    ]

    # ========================================================
    # ENDPOINT RISK
    # ========================================================

    endpoint_average_risk = [
        {
            "endpoint": row.endpoint,
            "average_risk": round(
                float(row.avg_risk),
                2
            )
        }
        for row in endpoint_stats
    ]

    # ========================================================
    # RECENT REQUESTS
    # ========================================================

    recent_logs = (
        db.query(RequestLog)
        .filter(RequestLog.user_id == user.id)
        .order_by(RequestLog.created_at.desc())
        .limit(50)
        .all()
    )

    recent_requests = []

    for log in recent_logs:

        recent_requests.append({

            "timestamp": (
                log.created_at.isoformat()
                if log.created_at
                else ""
            ),

            "endpoint": log.endpoint,

            "email": log.email,

            "ip_address": log.ip,

            "risk_score": float(log.risk_score),

            "is_overage": log.is_overage

        })

    # ========================================================
    # RESPONSE
    # ========================================================

    return {

        "requests_today": requests_today,

        "requests_this_week": requests_this_week,

        "most_used_endpoint": most_used_endpoint,

        "most_used_endpoint_risk": most_used_endpoint_risk,

        "daily_usage": daily_usage,

        "endpoint_breakdown": endpoint_breakdown,

        "endpoint_average_risk": endpoint_average_risk,

        "recent_requests": recent_requests

    }