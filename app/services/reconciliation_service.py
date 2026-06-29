from sqlalchemy.orm import Session
import redis
import os

from app.models.request_log import RequestLog
from app.services.metering_service import (
    get_usage,
    get_usage_key
)

# ============================================================
# REDIS
# ============================================================

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# ============================================================
# REDIS + DB RECONCILIATION
# ============================================================

def reconcile_usage(
    db: Session,
    user_id: int
):
    """
    Redis is the fast cache.

    PostgreSQL is the source of truth.

    If Redis becomes inaccurate (restart, eviction, etc.),
    rebuild it from the database.
    """

    redis_usage = get_usage(user_id)

    db_usage = (
        db.query(RequestLog)
        .filter(RequestLog.user_id == user_id)
        .count()
    )

    # Repair Redis if needed
    if redis_usage != db_usage:

        key = get_usage_key(user_id)

        redis_client.set(key, db_usage)

        redis_usage = db_usage

    return {
        "user_id": user_id,
        "redis_usage": redis_usage,
        "database_usage": db_usage,
        "reconciled": redis_usage == db_usage
    }