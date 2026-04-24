from app.db.redis import redis_client

RATE_LIMIT = 10
WINDOW = 60  # seconds

def check_rate_limit(user_id: int):
    key = f"rate_limit:{user_id}"

    current = redis_client.get(key)

    if current is None:
        redis_client.set(key, 1, ex=WINDOW)
        return True

    current = int(current)

    if current >= RATE_LIMIT:
        return False

    redis_client.incr(key)
    return True