import time

import redis
from fastapi import HTTPException

from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


# Sliding window with Redis sorted set.
def check_rate_limit(user_id: str):
    admin_users = {u.strip() for u in settings.admin_users.split(",") if u.strip()}
    if user_id in admin_users:
        return

    key = f"ratelimit:{user_id}"
    now = time.time()
    window_start = now - 60

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    _, count = pipe.execute()

    if int(count) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({settings.rate_limit_per_minute}/minute)",
            headers={"Retry-After": "60"},
        )

    pipe = redis_client.pipeline()
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, 120)
    pipe.execute()
