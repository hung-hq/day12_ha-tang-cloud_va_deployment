from datetime import datetime, timezone

import redis
from fastapi import HTTPException

from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def _monthly_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"budget:{user_id}:{month}"


def estimate_cost_usd(question: str, answer: str) -> float:
    input_tokens = max(1, len(question.split()) * 2)
    output_tokens = max(1, len(answer.split()) * 2) if answer else 1
    return (input_tokens / 1000 * 0.00015) + (output_tokens / 1000 * 0.0006)


def check_budget(user_id: str, estimated_cost: float):
    key = _monthly_key(user_id)
    current = float(redis_client.get(key) or 0.0)
    if current + estimated_cost > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Monthly budget exceeded for user {user_id}. "
                f"Current=${current:.4f}, budget=${settings.monthly_budget_usd:.2f}"
            ),
        )


def record_spending(user_id: str, amount: float):
    key = _monthly_key(user_id)
    pipe = redis_client.pipeline()
    pipe.incrbyfloat(key, amount)
    pipe.expire(key, 32 * 24 * 3600)
    pipe.execute()
