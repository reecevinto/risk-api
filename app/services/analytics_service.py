from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.request_log import RequestLog

# ============================================================
# DAY 7 PHASE 2
# STRIPE-LIKE USAGE ANALYTICS ENGINE
# ============================================================


def get_usage_analytics(db: Session, user_id: int):
    """
    Returns Stripe-style analytics for a user.

    Includes:
    • Total requests
    • Average risk score
    • Requests today
    • Requests this week
    • Daily usage (last 7 days)
    • Endpoint breakdown
    • Most-used endpoint
    • Average risk by endpoint
    • Overage requests
    • Overage percentage
    """

    # ========================================================
    # BASIC TOTALS
    # ========================================================

    total_requests = (
        db.query(RequestLog)
        .filter(RequestLog.user_id == user_id)
        .count()
    )

    average_risk = (
        db.query(func.avg(RequestLog.risk_score))
        .filter(RequestLog.user_id == user_id)
        .scalar()
    ) or 0

    # ========================================================
    # TODAY
    # ========================================================

    today = datetime.utcnow().date()

    requests_today = (
        db.query(RequestLog)
        .filter(
            RequestLog.user_id == user_id,
            func.date(RequestLog.created_at) == today,
        )
        .count()
    )

    # ========================================================
    # LAST 7 DAYS
    # ========================================================

    week_start = datetime.utcnow() - timedelta(days=7)

    requests_this_week = (
        db.query(RequestLog)
        .filter(
            RequestLog.user_id == user_id,
            RequestLog.created_at >= week_start,
        )
        .count()
    )

    # ========================================================
    # DAILY TREND
    # ========================================================

    daily_usage = (
        db.query(
            func.date(RequestLog.created_at),
            func.count(RequestLog.id),
        )
        .filter(
            RequestLog.user_id == user_id,
            RequestLog.created_at >= week_start,
        )
        .group_by(func.date(RequestLog.created_at))
        .order_by(func.date(RequestLog.created_at))
        .all()
    )

    daily_breakdown = [
        {
            "date": str(day),
            "requests": count,
        }
        for day, count in daily_usage
    ]

    # ========================================================
    # ENDPOINT BREAKDOWN
    # ========================================================

    endpoint_usage = (
        db.query(
            RequestLog.endpoint,
            func.count(RequestLog.id),
        )
        .filter(RequestLog.user_id == user_id)
        .group_by(RequestLog.endpoint)
        .order_by(func.count(RequestLog.id).desc())
        .all()
    )

    endpoint_breakdown = [
        {
            "endpoint": endpoint,
            "requests": count,
        }
        for endpoint, count in endpoint_usage
    ]

    # ========================================================
    # MOST USED ENDPOINT
    # ========================================================

    most_used_endpoint = (
        endpoint_usage[0][0]
        if endpoint_usage
        else None
    )

    # ========================================================
    # RISK PER ENDPOINT
    # ========================================================

    endpoint_risk = (
        db.query(
            RequestLog.endpoint,
            func.avg(RequestLog.risk_score),
        )
        .filter(RequestLog.user_id == user_id)
        .group_by(RequestLog.endpoint)
        .all()
    )

    endpoint_risk_breakdown = [
        {
            "endpoint": endpoint,
            "average_risk": round(avg, 2),
        }
        for endpoint, avg in endpoint_risk
    ]

    # ========================================================
    # OVERAGE
    # ========================================================

    overage_requests = (
        db.query(RequestLog)
        .filter(
            RequestLog.user_id == user_id,
            RequestLog.is_overage == True,
        )
        .count()
    )

    overage_percentage = (
        round((overage_requests / total_requests) * 100, 2)
        if total_requests
        else 0
    )

    # ========================================================
    # RECENT REQUESTS
    # ========================================================

    recent_requests = (
        db.query(RequestLog)
        .filter(RequestLog.user_id == user_id)
        .order_by(RequestLog.created_at.desc())
        .limit(10)
        .all()
    )

    # Convert to JSON
    recent_requests_data = [
        {
            "email": r.email,
            "phone": r.phone,
            "ip": r.ip,
            "endpoint": r.endpoint,
            "risk_score": r.risk_score,
            "trust_level": r.trust_level,
            "flags": r.flags,
            "created_at": r.created_at,
            "is_overage": r.is_overage,
        }
        for r in recent_requests
    ]

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "total_requests": total_requests,
        "average_risk_score": round(float(average_risk), 2),
        "requests_today": requests_today,
        "requests_this_week": requests_this_week,
        "daily_usage": daily_breakdown,
        "endpoint_breakdown": endpoint_breakdown,
        "most_used_endpoint": most_used_endpoint,
        "endpoint_average_risk": endpoint_risk_breakdown,
        "overage_requests": overage_requests,
        "overage_percentage": overage_percentage,
        "recent_requests": recent_requests_data,
    }