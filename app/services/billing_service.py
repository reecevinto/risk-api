from sqlalchemy.orm import Session
from app.models.request_log import RequestLog
from app.models.plan import Plan

def check_usage_limit(
    db: Session,
    user
):
    # 🔹 get user's plan
    plan = db.query(Plan).filter(Plan.id == user.plan_id).first()

    if not plan:
        return True

    # 🔹 count requests
    total_requests = db.query(RequestLog)\
        .filter(RequestLog.user_id == user.id)\
        .count()

    # 🔹 enforce limit
    return total_requests < plan.request_limit