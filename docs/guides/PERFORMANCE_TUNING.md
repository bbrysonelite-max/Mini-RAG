# Mini-RAG Performance Tuning Guide

Optimize your Mini-RAG deployment for high throughput and low latency.

---

## Database Connection Pooling

### PostgreSQL Pool Configuration

The app uses `psycopg-pool` for async connection pooling. Configure via environment variables:

```bash
# Connection pool size (default: 10)
export DATABASE_POOL_MIN_SIZE=5
export DATABASE_POOL_MAX_SIZE=20

# Connection timeout (seconds)
export DATABASE_POOL_TIMEOUT=30

# Maximum idle time before connection recycling (seconds)
export DATABASE_POOL_MAX_IDLE=300
```

### Optimal Settings by Load

| Deployment Size | Min Pool | Max Pool | Timeout |
|-----------------|----------|----------|---------|
| **Dev/Test** | 2 | 5 | 10s |
| **Small (<100 req/min)** | 5 | 10 | 20s |
| **Medium (100-1000 req/min)** | 10 | 30 | 30s |
| **Large (>1000 req/min)** | 20 | 50 | 60s |

### Monitor Pool Health

```python
# In server.py or admin endpoint
from database import get_pool_stats

stats = get_pool_stats()
print(f"Connections: {stats['size']} / {stats['max_size']}")
print(f"Idle: {stats['idle']}, Busy: {stats['busy']}")
```

---

## Redis Caching

### Enable Redis

```bash
export REDIS_ENABLED=true
export REDIS_URL="redis://localhost:6379/0"

# Cache TTLs (seconds)
export QUERY_CACHE_TTL=3600      # 1 hour for query results
export EMBEDDING_CACHE_TTL=86400  # 24 hours for embeddings
export STATS_CACHE_TTL=300        # 5 minutes for stats
```

### Redis Memory Configuration

Edit `redis.conf`:

```conf
# Set max memory (adjust for your server)
maxmemory 2gb

# Eviction policy (LRU is good for cache)
maxmemory-policy allkeys-lru

# Persistence (optional for cache-only use)
save ""
appendonly no
```

### Cache Hit Rate Monitoring

```bash
# Check cache metrics
curl http://localhost:8000/api/v1/cache/metrics

# Expected output
{
  "enabled": true,
  "hits": 15234,
  "misses": 3421,
  "hit_rate": 0.817,
  "keys": 1891,
  "memory_used": "512.3M"
}
```

**Target hit rate:** >70% for steady-state workloads

### When to Invalidate Cache

Cache is automatically invalidated on:
- Document ingestion (workspace-scoped)
- Source deletion
- Dedupe/rebuild operations

Manual invalidation:
```python
from cache_service import get_cache_service

cache = get_cache_service()
cache.invalidate_workspace(workspace_id="workspace-uuid")
```

---

## Request Deduplication

Prevents duplicate concurrent requests from executing expensive operations multiple times.

### How It Works

1. Client A submits: `"What is RAG?"`
2. Client B submits: `"What is RAG?"` (1ms later)
3. System executes once, both get the same result

### Configuration

```bash
# Deduplication TTL (seconds) - how long to track requests
export DEDUP_TTL=30
```

### Monitoring

```python
from request_dedup import get_deduplicator

dedup = get_deduplicator()
stats = dedup.get_stats()

print(f"Pending: {stats['pending_requests']}")
print(f"Waiters: {stats['total_waiters']}")
print(f"Savings: {stats['dedup_savings']} executions avoided")
```

---

## Index Warmup

The search index is loaded into memory on startup. For large corpora, this can take time.

### Current Behavior

- Index loads lazily on first query (cold start penalty)
- Subsequent queries are fast

### Optimization: Warm on Startup

```python
# In server.py startup event
@app.on_event("startup")
async def warmup():
    ensure_index()  # Load index immediately
    logger.info("Index warmed and ready")
```

### Monitor Index Load Time

```bash
# Check logs
grep "index.warm" logs/rag.log

# Should see:
# {"event":"index.warm_started","chunks":15234}
# {"event":"index.warm_completed","duration_ms":345}
```

---

## LLM Request Optimization

### Embedding Caching

Embeddings are expensive - cache aggressively:

```bash
# Long TTL for embeddings (they rarely change)
export EMBEDDING_CACHE_TTL=604800  # 7 days
```

### Batch Embeddings

When ingesting multiple documents, batch embedding requests:

```python
# Instead of:
for chunk in chunks:
    embedding = await get_embedding(chunk.content)

# Do:
texts = [chunk.content for chunk in chunks]
embeddings = await get_embeddings_batch(texts)  # Single API call
```

### Rate Limit Handling

```python
import asyncio

async def get_embedding_with_retry(text: str, retries=3):
    for attempt in range(retries):
        try:
            return await openai_client.embeddings.create(...)
        except RateLimitError:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

---

## Background Job Queue

Offload expensive operations to background workers.

### Enable Background Jobs

```bash
export BACKGROUND_JOBS_ENABLED=true
```

### Queue Heavy Operations

- `POST /api/rebuild` → returns job ID immediately
- `POST /api/dedupe` → queued
- Large ingestions (>100 files) → queued

### Monitor Queue Health

```bash
curl http://localhost:8000/api/v1/jobs?limit=50

# Prometheus metrics
curl http://localhost:8000/metrics | grep job_
# job_queue_depth 3
# job_completion_duration_seconds_bucket{status="success"} 45
```

---

## Load Balancing

### Horizontal Scaling

Mini-RAG is stateless (except for in-memory index). Scale horizontally:

```yaml
# docker-compose.yml
services:
  app:
    image: mini-rag:latest
    deploy:
      replicas: 3
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
```

### Sticky Sessions

If using in-memory cache only (no Redis), enable sticky sessions:

```nginx
# nginx.conf
upstream mini_rag {
    ip_hash;  # Sticky sessions
    server mini-rag-1:8000;
    server mini-rag-2:8000;
    server mini-rag-3:8000;
}
```

### Health Check Configuration

```nginx
location /health {
    proxy_pass http://mini_rag;
    proxy_connect_timeout 5s;
    proxy_read_timeout 10s;
}
```

---

## Chunking Strategy

### Current Defaults

- Chunk size: 512 tokens
- Overlap: 50 tokens

### Optimize for Your Use Case

**Long-form Q&A:** Larger chunks, less overlap
```python
# In raglite.py
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 100
```

**Precise citation:** Smaller chunks, more overlap
```python
CHUNK_SIZE = 256
CHUNK_OVERLAP = 64
```

### Impact on Performance

| Chunk Size | Pros | Cons |
|------------|------|------|
| **Small (256)** | Precise citations, faster embedding | More chunks to index, slower retrieval |
| **Medium (512)** | Balanced | Default - good for most cases |
| **Large (1024)** | Fewer chunks, faster retrieval | Less precise, larger embeddings |

---

## Database Query Optimization

### Index Usage

The schema includes indexes on:
- `users(email)` - for auth lookups
- `workspaces(organization_id)` - for org queries
- `api_keys(key_hash)` - for API key verification
- `workspace_usage_counters(workspace_id, period_start)` - for quota checks

### Analyze Slow Queries

```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log queries >100ms
SELECT pg_reload_conf();

-- Check slow query log
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Vacuum & Analyze

```bash
# Weekly maintenance
psql $DATABASE_URL -c "VACUUM ANALYZE;"
```

---

## Monitoring Dashboard Queries

### Grafana Query Examples

**Request Rate (per second):**
```promql
rate(ask_requests_total[5m])
```

**P95 Latency:**
```promql
histogram_quantile(0.95, rate(ask_request_latency_seconds_bucket[5m]))
```

**Cache Hit Rate:**
```promql
rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])
```

**Database Connection Pool Usage:**
```promql
db_pool_connections{state="busy"} / db_pool_connections{state="max"}
```

---

## Troubleshooting Performance Issues

### Issue: High /ask Latency

**Symptoms:** P95 >3s

**Diagnosis:**
1. Check embedding provider latency: `grep "openai.embed" logs/rag.log | jq '.duration_ms'`
2. Check BM25 index size: `curl http://localhost:8000/api/v1/stats`
3. Check database pool saturation: `grep "pool" logs/rag.log`

**Solutions:**
- Enable Redis caching
- Increase database pool size
- Use faster embedding model (e.g., `text-embedding-3-small`)

### Issue: Memory Growth

**Symptoms:** OOM kills, gradual memory increase

**Diagnosis:**
```bash
# Check process memory
ps aux | grep uvicorn

# Check Redis memory
redis-cli INFO memory
```

**Solutions:**
- Set Redis `maxmemory` limit
- Restart workers periodically (Kubernetes: `restartPolicy: Always`)
- Reduce in-memory index size (offload to pgvector)

### Issue: Database Connection Exhaustion

**Symptoms:** `PoolTimeout` errors

**Diagnosis:**
```python
from database import db
print(db.pool._queue.qsize())  # Available connections
```

**Solutions:**
- Increase `DATABASE_POOL_MAX_SIZE`
- Check for connection leaks (ensure `async with db.pool.connection()`)
- Add connection timeout monitoring

---

## Benchmarking

### Load Testing with Apache Bench

```bash
# Test /health endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# Test authenticated /ask endpoint
ab -n 100 -c 5 \
   -H "X-API-Key: mrag_..." \
   -p query.json \
   -T "application/json" \
   http://localhost:8000/api/v1/ask
```

### Locust Load Test

See `scripts/load_test.py` for comprehensive load testing scenarios.

```bash
pip install locust
locust -f scripts/load_test.py --host http://localhost:8000
# Open http://localhost:8089 for UI
```

---

**Next Steps:**
- Set up Grafana dashboards (`docs/infra/metrics_alerts/`)
- Enable Redis caching
- Configure connection pooling
- Run load tests before production deploy

