import redis

redis_client = redis.Redis(
    host="risk-redis",
    port=6379,
    decode_responses=True
)