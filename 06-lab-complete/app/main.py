import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, estimate_cost_usd, record_spending
from app.rate_limiter import check_rate_limit
from utils.mock_llm import ask as llm_ask

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
REQUEST_COUNT = 0
ERROR_COUNT = 0
IS_READY = False
SHUTTING_DOWN = False

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def _log_event(**payload):
    logger.info(json.dumps(payload))


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def _load_history(user_id: str) -> list[dict]:
    key = _history_key(user_id)
    raw = redis_client.lrange(key, 0, -1)
    return [json.loads(item) for item in raw]


def _append_history(user_id: str, role: str, content: str):
    key = _history_key(user_id)
    message = json.dumps(
        {
            "role": role,
            "content": content,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )
    redis_client.rpush(key, message)
    redis_client.ltrim(key, -settings.history_max_messages, -1)
    redis_client.expire(key, settings.history_ttl_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global IS_READY
    redis_client.ping()
    IS_READY = True
    _log_event(event="startup", app=settings.app_name, env=settings.environment)
    yield
    IS_READY = False
    _log_event(event="shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.allowed_origins.split(",") if item.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-User-Id"],
)


@app.middleware("http")
async def http_middleware(request: Request, call_next):
    global REQUEST_COUNT, ERROR_COUNT

    if SHUTTING_DOWN and request.url.path not in ["/health", "/ready"]:
        raise HTTPException(status_code=503, detail="Server is shutting down")

    started = time.time()
    REQUEST_COUNT += 1
    try:
        response: Response = await call_next(request)
    except Exception:
        ERROR_COUNT += 1
        raise

    elapsed_ms = round((time.time() - started) * 1000, 2)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    _log_event(
        event="request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=elapsed_ms,
    )
    return response


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    history_length: int
    timestamp: str


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.post("/ask", response_model=AskResponse)
def ask_agent(
    body: AskRequest,
    user_id: str = Depends(verify_api_key),
):
    check_rate_limit(user_id)

    history = _load_history(user_id)
    estimated = estimate_cost_usd(body.question, "")
    check_budget(user_id, estimated)

    _append_history(user_id, "user", body.question)
    answer = llm_ask(body.question, history)
    _append_history(user_id, "assistant", answer)

    final_cost = estimate_cost_usd(body.question, answer)
    record_spending(user_id, final_cost)

    history_size = len(_load_history(user_id))

    return AskResponse(
        user_id=user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        history_length=history_size,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/history")
def get_history(user_id: str = Depends(verify_api_key)):
    return {
        "user_id": user_id,
        "messages": _load_history(user_id),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "requests": REQUEST_COUNT,
        "errors": ERROR_COUNT,
    }


@app.get("/ready")
def ready():
    if not IS_READY:
        raise HTTPException(status_code=503, detail="Not ready")
    try:
        redis_client.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc
    return {"ready": True}


def _handle_sigterm(signum, _frame):
    global SHUTTING_DOWN, IS_READY
    SHUTTING_DOWN = True
    IS_READY = False
    _log_event(event="signal", signum=signum)


signal.signal(signal.SIGTERM, _handle_sigterm)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
