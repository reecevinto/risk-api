import os
import stripe
import redis
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.user import User

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# ============================================================
# REDIS CLIENT (ADDED)
# ============================================================
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


# ============================================================
# PLAN LIMITS (ADDED)
# ============================================================
PLAN_LIMITS = {
    "free": 20,
    "pro": 200,
    "enterprise": 10**9
}


# ============================================================
# CHECK USAGE LIMIT (ADDED - FIX FOR YOUR CRASH)
# ============================================================
def check_usage_limit(user: User) -> bool:
    """
    Redis-based daily usage tracking per user.
    """

    user_id = str(user.id)
    plan = user.plan or "free"

    limit = PLAN_LIMITS.get(plan, 20)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"usage:{user_id}:{today}"

    current_usage = redis_client.get(key)

    if current_usage is None:
        redis_client.set(key, 1, ex=86400)  # 24h reset
        return True

    current_usage = int(current_usage)

    if current_usage >= limit:
        return False

    redis_client.incr(key)
    return True


# ============================================================
# CREATE CHECKOUT SESSION
# ============================================================
def create_checkout_session(user: User, price_id: str):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        success_url="http://localhost:3000/success",
        cancel_url="http://localhost:3000/cancel",
        metadata={
            "user_id": user.id
        }
    )

    return session.url


# ============================================================
# UPDATE USER PLAN AFTER PAYMENT
# ============================================================
def activate_subscription(db: Session, user_id: int, plan: str):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return None

    user.plan = plan
    db.commit()

    return user

# ============================================================
# GET USER PLAN (ADDED - FIX IMPORT ERROR)
# ============================================================
def get_user_plan(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return None

    return user.plan