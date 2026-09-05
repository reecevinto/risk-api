from sqlalchemy.orm import Session
import redis
import os

from app.models.user import User
from app.models.request_log import RequestLog
from app.services.metering_service import (
    get_current_usage as get_usage
)

# ============================================================
# REDIS
# ============================================================

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# Helper function for Redis cache key format
def get_usage_key(user_id: int) -> str:
    return f"usage:user:{user_id}"

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

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    # Fetch source-of-truth usage from PostgreSQL via metering_service
    db_usage = get_usage(db, user)

    key = get_usage_key(user_id)
    raw_redis_val = redis_client.get(key)
    redis_usage = int(raw_redis_val) if raw_redis_val is not None else -1

    # Repair Redis if out of sync or missing
    if redis_usage != db_usage:
        redis_client.set(key, db_usage)
        redis_usage = db_usage

    return {
        "user_id": user_id,
        "redis_usage": redis_usage,
        "database_usage": db_usage,
        "reconciled": True
    }