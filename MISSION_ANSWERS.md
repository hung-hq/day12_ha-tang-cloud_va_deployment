# Day 12 Lab - Mission Answers

Student: Hoang Quoc Hung  
Student ID: 2A202600071  
Date: 2026-04-17

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. Hardcoded secrets in code (`OPENAI_API_KEY`, `DATABASE_URL`) in develop app.
2. Debug mode is always enabled (`DEBUG = True`) and auto reload is used.
3. Logs expose secret values (`print` includes API key).
4. No health/readiness endpoints, so platform cannot auto-detect failures.
5. Host and port are fixed (`localhost:8000`), not driven by environment variables.
6. App binds to `localhost`, not `0.0.0.0`, so container/cloud access fails.
7. No graceful shutdown handling for `SIGTERM`.

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcoded constants in source | Env-based config via settings | Supports 12-factor app and multiple environments safely |
| Secrets | Exposed in source/logs | Loaded from env vars | Prevents credential leakage |
| Logging | `print()` plain text | Structured JSON logging | Easier monitoring/search in cloud logs |
| Health check | Missing | `GET /health` | Enables liveness probe and auto-restart |
| Readiness check | Missing | `GET /ready` | Prevents routing traffic before app is ready |
| Host/Port | Fixed localhost:8000 | `HOST`/`PORT` from env | Compatible with Railway/Render runtime |
| Shutdown | Abrupt | SIGTERM-aware graceful flow | Reduces dropped requests on deploy/restart |
| CORS | Not controlled | Configurable allow list | Safer browser integration |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image (develop): `python:3.11`.
2. Working directory: `/app`.
3. `COPY requirements.txt` before source code to leverage Docker layer cache, avoiding full reinstall when only app code changes.
4. `CMD` provides default runtime command (can be overridden). `ENTRYPOINT` fixes the executable and is harder to override.

### Exercise 2.3: Image size comparison
- Develop: not measured in this workspace run.
- Production: not measured in this workspace run.
- Difference: production should be significantly smaller because it uses multi-stage build + `python:3.11-slim` runtime + copies only runtime artifacts.

Commands to fill exact numbers:
```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images my-agent:develop my-agent:advanced
```

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://day12-agent-deployment-production-f279.up.railway.app
- Screenshot: added in `screenshots/` folder.

### Exercise 3.2: Railway vs Render config differences
- Railway uses `railway.toml` with build/deploy blocks (`startCommand`, `healthcheckPath`, restart policy).
- Render uses `render.yaml` Blueprint with service definitions (`type: web`, `envVars`, region/plan, optional managed Redis).
- Both support env vars and health checks, but manifest structure differs by platform.

## Part 4: API Security

### Exercise 4.1-4.3: Test results (based on implementation)
- Missing or invalid API key -> HTTP 401 (`Invalid or missing API key`).
- Valid API key -> request accepted.
- Rate limiter algorithm: Sliding window using Redis Sorted Set (`ZREMRANGEBYSCORE`, `ZCARD`, `ZADD`).
- Limit: `RATE_LIMIT_PER_MINUTE` (default 10 req/min).
- Admin bypass: users listed in `ADMIN_USERS` skip rate limiting.
- Live test on Railway: 15 rapid requests produced `200` for first 10 calls and `429` for remaining calls.

### Exercise 4.4: Cost guard implementation
- Monthly key format: `budget:<user_id>:YYYY-MM` in Redis.
- `check_budget` reads current monthly spend and blocks with HTTP 402 when adding estimated cost exceeds `MONTHLY_BUDGET_USD` (default $10).
- `record_spending` updates spending with `INCRBYFLOAT` and sets TTL (~32 days).
- Cost estimate uses rough token proxy from question/answer length.
- Live test on Railway: temporarily set `MONTHLY_BUDGET_USD=0.000001`, redeployed, and received HTTP `402`; then restored budget to `10.0` and verified normal `200` responses.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
1. Health endpoint (`/health`): returns status, uptime, request/error counters.
2. Readiness endpoint (`/ready`): checks app readiness flag + Redis ping; returns 503 when unavailable.
3. Graceful shutdown: handles `SIGTERM`, sets `SHUTTING_DOWN=True`, stops readiness, rejects new traffic with 503 while in-flight requests finish.
4. Stateless design: conversation history stored in Redis (`history:<user_id>`) instead of in-memory dict.
5. Load balancing and scale: `docker-compose.yml` includes Nginx reverse proxy + agent replicas (`deploy.replicas: 3`) + Redis shared backend.
6. No hardcoded production secrets: settings loaded from `.env`/`.env.local` and environment variables.

## Final Notes
- Core production requirements are implemented in `06-lab-complete`.
- Public deployment URL is active and screenshot files are included in `screenshots/`.
