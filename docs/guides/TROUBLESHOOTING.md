# Mini-RAG Troubleshooting Runbook

Quick diagnosis and resolution for common production issues.

---

## 🚨 Critical Alerts

### Service Down / Health Check Failing

**Symptoms:** `/health` returns 500 or times out

**Diagnosis:**
```bash
# Check if service is running
curl -v http://localhost:8000/health

# Check logs
docker logs mini-rag-app --tail 100

# Check process
ps aux | grep uvicorn
```

**Common Causes:**
1. **Database unavailable** → health check fails
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```
   **Fix:** Restart database, check connection string

2. **Out of memory** → process killed by OOM
   ```bash
   dmesg | grep -i "out of memory"
   ```
   **Fix:** Increase memory limits, add swap, optimize index size

3. **Port already in use**
   ```bash
   lsof -i :8000
   ```
   **Fix:** Kill conflicting process or change port

### Database Connection Pool Exhausted

**Symptoms:** `PoolTimeout` errors, slow requests

**Diagnosis:**
```python
# Check pool stats
from database import get_pool_stats
stats = get_pool_stats()
print(f"{stats['busy']} / {stats['max_size']} connections busy")
```

**Fix:**
```bash
# Increase pool size
export DATABASE_POOL_MAX_SIZE=50

# Or find connection leaks
grep "pool.*acquire" logs/rag.log | wc -l  # acquisitions
grep "pool.*release" logs/rag.log | wc -l  # releases
# If acquire > release, you have a leak
```

### High Latency (P95 > 5s)

**Symptoms:** Slow responses, user complaints

**Diagnosis:**
```bash
# Check metrics
curl http://localhost:8000/metrics | grep latency_seconds

# Find slow requests in logs
grep "ask.completed" logs/rag.log | jq 'select(.duration_ms > 5000)'
```

**Common Causes:**
1. **OpenAI/embedding provider slow**
   - Check OpenAI status page
   - Enable caching: `export REDIS_ENABLED=true`

2. **Large corpus, slow BM25**
   - Check chunk count: `curl http://localhost:8000/api/v1/stats`
   - Migrate to pgvector for >100k chunks

3. **Database queries slow**
   ```sql
   SELECT * FROM pg_stat_statements
   ORDER BY mean_exec_time DESC LIMIT 10;
   ```
   - Add missing indexes
   - Run `VACUUM ANALYZE`

---

## ⚠️ Common Errors

### 401 Unauthorized

**Error:** `{"detail":"Not authenticated"}`

**Causes:**
1. Missing API key/JWT cookie
2. Expired JWT (>7 days old)
3. Invalid API key

**Debug:**
```bash
# Test with API key
curl -H "X-API-Key: mrag_..." http://localhost:8000/api/v1/ask

# Check API key in database
psql $DATABASE_URL -c "SELECT id, user_id, scopes FROM api_keys WHERE revoked_at IS NULL;"
```

**Fix:**
- Generate new API key: `python scripts/manage_api_keys.py create --user <uuid> --scope read`
- Or login via OAuth: visit `/auth/google`

### 429 Rate Limited

**Error:** `{"detail":"Rate limit exceeded"}`

**Causes:**
1. Too many requests from same client
2. Quota exceeded for workspace

**Debug:**
```bash
# Check SlowAPI limits (30/min for /ask, 10/hour for uploads)
grep "rate_limit" logs/rag.log

# Check workspace quotas
curl -H "X-API-Key: mrag_admin_..." \
  http://localhost:8000/metrics | grep workspace_quota
```

**Fix:**
```sql
-- Increase workspace quotas
UPDATE workspace_quota_settings
SET request_limit_per_day = 10000,
    request_limit_per_minute = 100
WHERE workspace_id = 'workspace-uuid';
```

### 402 Payment Required

**Error:** `{"detail":"Workspace billing status 'past_due' does not permit ingestion"}`

**Causes:**
- Trial expired
- Subscription canceled
- Payment failed

**Debug:**
```sql
SELECT name, billing_status, trial_ends_at, subscription_expires_at
FROM organizations;
```

**Fix:**
```bash
# Option 1: Admin override (temporary)
curl -X PATCH \
  -H "X-API-Key: mrag_admin_..." \
  -H "Content-Type: application/json" \
  -d '{"billing_status":"active"}' \
  http://localhost:8000/api/v1/admin/billing/<org_id>

# Option 2: Process payment via Stripe portal
curl -X POST \
  -H "X-API-Key: mrag_admin_..." \
  -H "Content-Type: application/json" \
  -d '{"return_url":"http://app"}' \
  http://localhost:8000/api/v1/billing/portal
# → redirect user to returned URL
```

### 500 Internal Server Error

**Generic error, need to check logs**

**Debug:**
```bash
# Check recent errors
grep "ERROR" logs/rag.log | tail -20

# Check specific request
grep "request_id.*<REQUEST_ID>" logs/rag.log | jq
```

**Common Causes:**
1. Unhandled exception → check stack trace in logs
2. External API failure (OpenAI, Stripe) → retry with exponential backoff
3. Database constraint violation → check data integrity

---

## 🐛 Feature-Specific Issues

### OAuth Login Not Working

**Symptoms:** `/auth/google` returns 500 or redirect fails

**Debug:**
```bash
# Check OAuth config
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
print('CLIENT_ID:', os.getenv('GOOGLE_CLIENT_ID'))
print('CLIENT_SECRET:', '***' if os.getenv('GOOGLE_CLIENT_SECRET') else 'MISSING')
"

# Check callback URL in Google Console
# Must match: https://yourdomain.com/auth/callback
```

**Fix:**
1. Set environment variables
2. Update redirect URI in Google Cloud Console
3. Restart server

### Embeddings/Vector Search Not Working

**Symptoms:** Queries return no results or all BM25

**Debug:**
```bash
# Check if OpenAI key is set
echo $OPENAI_API_KEY

# Check if pgvector extension exists
psql $DATABASE_URL -c "\dx"

# Test embedding generation
python3 -c "
from openai import AsyncOpenAI
import asyncio
client = AsyncOpenAI()
async def test():
    resp = await client.embeddings.create(input='test', model='text-embedding-3-small')
    print('Embedding:', len(resp.data[0].embedding), 'dimensions')
asyncio.run(test())
"
```

**Fix:**
- Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- Install pgvector: `CREATE EXTENSION vector;`
- Re-index: `POST /api/rebuild`

### Ingestion Fails Silently

**Symptoms:** Upload succeeds but chunks not appearing

**Debug:**
```bash
# Check ingestion logs
grep "ingest" logs/rag.log | jq '.event,.status'

# Check if background jobs enabled
echo $BACKGROUND_JOBS_ENABLED

# Check job status
curl http://localhost:8000/api/v1/jobs?limit=50
```

**Fix:**
- If `BACKGROUND_JOBS_ENABLED=true`, check job errors in `/api/v1/jobs`
- Check file format is supported (.pdf, .docx, .md, .txt, .vtt, .srt)
- Ensure billing is active (see 402 error above)

### Cache Not Working (Redis)

**Symptoms:** Cache metrics show 0 hits

**Debug:**
```bash
# Check if Redis is enabled
echo $REDIS_ENABLED

# Check Redis connectivity
redis-cli -u $REDIS_URL PING

# Check cache metrics
curl http://localhost:8000/api/v1/cache/metrics
```

**Fix:**
```bash
# Enable Redis
export REDIS_ENABLED=true
export REDIS_URL="redis://localhost:6379/0"

# Test connection
redis-cli -u $REDIS_URL INFO stats
```

---

## 📊 Performance Issues

### Memory Leak

**Symptoms:** Memory usage grows over time, eventual OOM

**Debug:**
```bash
# Monitor memory over time
while true; do
  ps aux | grep uvicorn | awk '{print $6}'
  sleep 300
done

# Check for leaks in Redis
redis-cli -u $REDIS_URL INFO memory
redis-cli -u $REDIS_URL DBSIZE
```

**Fix:**
- Set Redis `maxmemory` limit
- Restart workers periodically (e.g., daily)
- Check for circular references in cache

### Disk Space Full

**Symptoms:** Write failures, logs not rotating

**Debug:**
```bash
df -h
du -sh /var/log/*
du -sh backups/
```

**Fix:**
```bash
# Clean old backups (keep last 7 days)
find backups/ -name "*.jsonl" -mtime +7 -delete

# Rotate logs
logrotate /etc/logrotate.d/mini-rag

# Or manually
mv logs/rag.log logs/rag.log.old
touch logs/rag.log
```

### High CPU Usage

**Symptoms:** CPU at 100%, slow responses

**Debug:**
```bash
# Check which process
top -p $(pgrep uvicorn)

# Profile Python
pip install py-spy
py-spy top --pid $(pgrep uvicorn)
```

**Common Causes:**
- BM25 search on large corpus → migrate to pgvector
- Inefficient regex in chunking → optimize
- Too many concurrent requests → add rate limiting

---

## 🔍 Debugging Tools

### Live Tail Logs with Filtering

```bash
# All errors
tail -f logs/rag.log | jq 'select(.level=="ERROR")'

# Specific user
tail -f logs/rag.log | jq 'select(.user_id=="user-uuid")'

# Slow requests
tail -f logs/rag.log | jq 'select(.duration_ms > 3000)'
```

### Check Active Connections

```sql
-- PostgreSQL
SELECT * FROM pg_stat_activity WHERE datname = 'rag_brain';

-- Count by state
SELECT state, COUNT(*) FROM pg_stat_activity GROUP BY state;
```

### Inspect Request Flow

```bash
# Get request ID from logs or headers
REQUEST_ID="req_abc123"

# Follow entire request
grep "$REQUEST_ID" logs/rag.log | jq '.event,.duration_ms'

# Expected flow:
# ask.started → auth.resolved → quota.checked → retrieve.started → retrieve.completed → ask.completed
```

### Test Webhooks Locally

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Forward to local server
stripe listen --forward-to localhost:8000/api/v1/billing/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
```

---

## 📞 Escalation Checklist

Before escalating to engineering:

1. **Gather context:**
   - Request ID or trace ID
   - Timestamp of issue
   - Affected users/workspaces
   - Reproduction steps

2. **Collect logs:**
   ```bash
   # Last hour of errors
   grep "ERROR" logs/rag.log | grep "$(date -u +%Y-%m-%d)" > /tmp/errors.log
   
   # Specific request
   grep "req_abc123" logs/rag.log > /tmp/request.log
   ```

3. **Check metrics:**
   - Prometheus dashboard (latency, error rate)
   - Database health (connection pool, slow queries)
   - External services (OpenAI, Stripe status pages)

4. **Document temporary workaround:**
   - Did restarting fix it?
   - Did increasing resources help?
   - Is it isolated to one tenant?

---

**See Also:**
- `docs/guides/PERFORMANCE_TUNING.md` - Optimize slow deployments
- `docs/guides/DEPLOYMENT_CHECKLIST.md` - Pre-deployment validation
- `docs/infra/metrics_alerts/README.md` - Alert configurations

