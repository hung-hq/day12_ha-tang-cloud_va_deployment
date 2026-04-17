# Deployment Information

## Public URL
https://day12-agent-deployment-production-f279.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://day12-agent-deployment-production-f279.up.railway.app/health
# Actual: {"status":"ok","uptime_seconds":...,"requests":...,"errors":0}
```

### Readiness Check
```bash
curl https://day12-agent-deployment-production-f279.up.railway.app/ready
# Expected: {"ready": true}
```

### API Test (with authentication)
```bash
curl -X POST https://day12-agent-deployment-production-f279.up.railway.app/ask \
  -H "X-API-Key: hung-day12-key" \
  -H "X-User-Id: test-user" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

### Authentication Required Test
```bash
curl -X POST https://day12-agent-deployment-production-f279.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Actual: 401 Unauthorized
```

### Rate Limiting Test
```bash
for i in {1..15}; do
  curl -X POST https://day12-agent-deployment-production-f279.up.railway.app/ask \
    -H "X-API-Key: hung-day12-key" \
    -H "X-User-Id: test-user" \
    -H "Content-Type: application/json" \
    -d '{"question": "rate-limit-test"}'
done
# Expected: eventually return 429
```

Actual result:
- Status sequence: `200,200,200,200,200,200,200,200,200,200,429,429,429,429,429`

## Environment Variables Set
- PORT
- REDIS_URL
- AGENT_API_KEY
- ENVIRONMENT
- DEBUG
- JWT_SECRET
- RATE_LIMIT_PER_MINUTE
- MONTHLY_BUDGET_USD
- LOG_LEVEL or DEBUG

## Deployment Checklist
- [x] Public URL updated
- [x] Environment variables configured on platform
- [x] Health endpoint returns 200
- [x] Ready endpoint returns 200
- [x] Ask endpoint requires API key (401 without key)
- [x] Ask endpoint works with valid key (200)
- [x] Rate limiting returns 429 after threshold
- [x] Cost guard returns 402 when monthly budget exceeded

## Verified Test Outputs
- `GET /health` -> `200` with payload like `{"status":"ok","uptime_seconds":...,"requests":...,"errors":0}`
- `POST /ask` without API key -> `401`
- `POST /ask` with API key -> `200`
- Rate-limit stress test (15 calls) -> first 10 calls `200`, subsequent calls `429`
- Cost guard test (temporary `MONTHLY_BUDGET_USD=0.000001` + redeploy) -> `402`
- Post-restore test (`MONTHLY_BUDGET_USD=10.0`) -> deploy `SUCCESS`, authenticated `POST /ask` -> `200`

## Screenshots
- [x] Deployment dashboard (`screenshots/dashboard.png`)
- [x] Service running (`screenshots/running.png`)
- [x] Endpoint test results (`screenshots/test.png`)

## Notes
- Application source used for deployment: `06-lab-complete/`.
- If deploying on Railway: repository already includes `railway.toml`.
- If deploying on Render: repository already includes `render.yaml`.
- Railway project: `day12-agent-deployment`.
- Railway service domain is active and serving traffic.
