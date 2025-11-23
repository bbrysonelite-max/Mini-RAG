# Mini-RAG Architecture

## System Overview

Mini-RAG is a multi-tenant RAG (Retrieval-Augmented Generation) system built for production deployment with enterprise features.

```
┌─────────────────────────────────────────────────────────────┐
│                         Clients                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Browser  │  │  Mobile  │  │   SDK    │  │   CLI    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                          │
                   ┌──────▼──────┐
                   │  Load       │
                   │  Balancer   │
                   │  (nginx)    │
                   └──────┬──────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
   │  App    │       │  App    │      │  App    │
   │Instance1│       │Instance2│      │Instance3│
   └────┬────┘       └────┬────┘      └────┬────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
   │PostgreSQL│      │  Redis  │      │  File   │
   │+pgvector │      │ (Cache) │      │ Storage │
   └─────────┘       └─────────┘      └─────────┘
        │
   ┌────▼────────────────────────────┐
   │  External Services              │
   │  ┌────────┐  ┌────────┐  ┌────┐│
   │  │ OpenAI │  │ Stripe │  │OAuth││
   │  └────────┘  └────────┘  └────┘│
   └─────────────────────────────────┘
```

---

## Component Architecture

### FastAPI Application Layer

```
server.py
├── Middleware Stack
│   ├── CORS
│   ├── SessionMiddleware (JWT cookies)
│   ├── SlowAPI (rate limiting)
│   ├── Security Headers
│   └── OpenTelemetry Instrumentation
│
├── API Routes
│   ├── /auth/* (OAuth, JWT)
│   ├── /api/v1/ask (Query endpoint)
│   ├── /api/v1/sources (Document management)
│   ├── /api/v1/ingest/* (Document upload)
│   ├── /api/v1/admin/* (Admin operations)
│   ├── /api/v1/billing/* (Stripe integration)
│   └── /api/v1/jobs (Background task status)
│
└── Core Services
    ├── RAGPipeline (retrieval + generation)
    ├── QuotaService (usage tracking)
    ├── BillingService (Stripe)
    ├── ApiKeyService (API key management)
    ├── UserService (user/org/workspace)
    ├── CacheService (Redis)
    └── RequestDeduplicator (concurrent request optimization)
```

---

## Data Flow

### Query Request Flow

```
1. Client Request
   └─> POST /api/v1/ask {query, k}

2. Authentication & Authorization
   ├─> JWT Cookie or X-API-Key header
   ├─> Resolve user/workspace context
   └─> Check API key scopes (read required)

3. Quota Check
   ├─> Check workspace quotas
   └─> Increment request counter

4. Cache Lookup (if Redis enabled)
   ├─> Hash: query + k + workspace_id
   └─> If HIT: return cached result

5. Request Deduplication
   ├─> Check if identical query in-flight
   └─> If yes: wait for first to complete

6. Retrieval
   ├─> BM25 keyword search
   ├─> pgvector semantic search (if OpenAI key set)
   └─> Merge & rank chunks

7. Generation
   ├─> Format prompt with retrieved chunks
   ├─> Call LLM (OpenAI/Anthropic)
   └─> Parse & score answer

8. Cache Result (if Redis enabled)
   └─> Store with TTL (default 1 hour)

9. Metrics & Logging
   ├─> Prometheus: ask_request_latency_seconds
   ├─> Structured log: {"event":"ask.completed",...}
   └─> OpenTelemetry trace

10. Response
    └─> {answer, chunks, score, count}
```

### Ingestion Flow

```
1. Client Upload
   └─> POST /api/v1/ingest/files {files[], language}

2. Auth + Quota + Billing Check
   ├─> Requires 'write' scope
   ├─> Check chunk quota available
   └─> Check billing_status = 'active' or 'trialing'

3. File Processing
   ├─> Validate file type & size
   ├─> Generate safe filename
   ├─> Extract text (PDF, DOCX, etc.)
   └─> Split into chunks (512 tokens, 50 overlap)

4. Embedding Generation (if enabled)
   ├─> Check cache for each chunk
   ├─> Batch request to OpenAI
   └─> Cache embeddings (24h TTL)

5. Storage
   ├─> Append to chunks.jsonl (with backup)
   ├─> Tag with user_id + workspace_id
   └─> Update database metadata

6. Index Rebuild
   ├─> If background jobs enabled: enqueue
   └─> Else: rebuild immediately

7. Cache Invalidation
   └─> Clear workspace query cache

8. Response
    └─> {message, chunks_added, job_id?}
```

---

## Database Schema

### Core Tables

```sql
-- User Management
users (id, email, name, role, created_at)
  ├─> PK: id (UUID)
  └─> UNIQUE: email

-- Multi-Tenancy
organizations (id, name, slug, plan, billing_status, stripe_customer_id, ...)
  └─> 1:N workspaces

workspaces (id, name, organization_id, created_at)
  ├─> FK: organization_id → organizations
  └─> 1:N members

user_organizations (user_id, organization_id, role)
  ├─> FK: user_id → users
  └─> FK: organization_id → organizations

workspace_members (user_id, workspace_id, role)
  ├─> FK: user_id → users
  └─> FK: workspace_id → workspaces

-- API Keys
api_keys (id, key_hash, user_id, workspace_id, scopes[], created_at, revoked_at)
  ├─> PK: id (UUID)
  ├─> FK: user_id → users
  ├─> FK: workspace_id → workspaces
  └─> INDEX: key_hash

-- Quotas
workspace_quota_settings (workspace_id, chunk_limit, request_limit_per_day, ...)
  └─> FK: workspace_id → workspaces

workspace_usage_counters (workspace_id, period_start, requests_count, chunks_count)
  └─> Tracks daily usage

-- Billing
organization_billing_events (id, organization_id, event_id, event_type, payload, created_at)
  ├─> Stripe webhook event log
  └─> UNIQUE: event_id (idempotency)
```

### Chunk Storage

**Current:** JSONL files (`out/chunks.jsonl`)
```json
{
  "id": "hash",
  "source": {"type": "document", "path": "..."},
  "content": "...",
  "metadata": {"user_id": "...", "workspace_id": "..."},
  "embedding": [...]
}
```

**Future:** PostgreSQL table with pgvector
```sql
chunks (id, workspace_id, source_id, content, embedding vector(1536))
```

---

## Authentication & Authorization

### JWT Cookies (Browser Users)

```
1. User clicks "Sign in with Google"
   └─> GET /auth/google

2. Redirect to Google OAuth
   └─> User approves

3. Callback with authorization code
   └─> POST /auth/callback

4. Exchange code for user info
   ├─> Create/update user in database
   └─> Issue JWT (7-day expiry)

5. Set HttpOnly cookie
   └─> Subsequent requests include cookie

Token Payload:
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "admin",
  "exp": 1234567890
}
```

### API Keys (Programmatic Access)

```
1. Admin generates key
   └─> python scripts/manage_api_keys.py create --user <uuid> --scope read write

2. System generates random token
   ├─> mrag_<random_32_chars>
   └─> Stores SHA-256 hash in database

3. Client includes in header
   └─> X-API-Key: mrag_...

4. Server verifies
   ├─> Hash incoming key
   ├─> Lookup in database
   ├─> Check not revoked
   ├─> Check scopes
   └─> Resolve user/workspace context

Scopes:
- read: /ask, /sources (GET)
- write: /ingest/*, /sources (DELETE), /dedupe, /rebuild
- admin: /admin/*
```

---

## Caching Strategy

### Redis Cache Layers

```
┌─────────────────────────────────────┐
│  Cache Key Types                     │
├──────────────────────────┬──────────┤
│ query:<hash>             │ 1 hour   │  ← Query results
│ embedding:<hash>         │ 24 hours │  ← OpenAI embeddings
│ stats:system             │ 5 min    │  ← System stats
│ workspace:<id>:sources   │ 10 min   │  ← Source list
└──────────────────────────┴──────────┘

Cache Invalidation Events:
- Ingestion → Clear workspace queries
- Source delete → Clear workspace queries
- Dedupe/rebuild → Clear all queries
- Manual → Clear specific workspace
```

### Request Deduplication

Prevents duplicate concurrent requests:
```python
# Two clients ask "What is RAG?" simultaneously
# Only one execution, both get same result

deduplicator.deduplicate(
    key_data={"query": "What is RAG?", "k": 5, "workspace_id": "..."},
    executor=lambda: expensive_operation()
)
```

---

## Monitoring & Observability

### Prometheus Metrics

```
# Request metrics
ask_requests_total{workspace_id, status_code}
ask_request_latency_seconds_bucket{workspace_id, outcome}

# Ingestion metrics
ingest_operations_total{source, outcome}
ingest_processed_chunks_total{workspace_id}

# Quota metrics
workspace_quota_usage{workspace_id, metric}
workspace_quota_ratio{workspace_id, metric}
quota_exceeded_total{workspace_id, metric}

# External service metrics
external_request_errors_total{service}

# Background jobs
job_queue_depth
job_completion_duration_seconds{status}
```

### Structured Logging

Every log entry includes:
```json
{
  "timestamp": "2025-11-23T12:34:56Z",
  "level": "INFO",
  "event": "ask.completed",
  "request_id": "req_abc123",
  "trace_id": "7f3e...",
  "span_id": "5a4b...",
  "user_id": "user-uuid",
  "workspace_id": "workspace-uuid",
  "organization_id": "org-uuid",
  "duration_ms": 245,
  "outcome": "success"
}
```

### OpenTelemetry Traces

Distributed tracing through:
- Internal service calls
- External APIs (OpenAI, Stripe)
- Database queries
- Cache operations

Trace context propagated via:
- `X-Request-ID` header
- `traceparent` header (W3C standard)

---

## Scaling Considerations

### Horizontal Scaling

**Stateless Components:**
- FastAPI app (scale to N instances)
- Background workers (scale independently)

**Stateful Components:**
- PostgreSQL (read replicas)
- Redis (cluster mode)
- File storage (S3/shared NFS)

### Load Balancing

```nginx
upstream mini_rag {
    least_conn;  # or ip_hash for sticky sessions
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    location / {
        proxy_pass http://mini_rag;
        proxy_set_header X-Request-ID $request_id;
        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
    }
}
```

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **P95 Latency** | <2s | With cache hit |
| **P99 Latency** | <5s | Cold path |
| **Throughput** | 100 req/s | Per instance |
| **Availability** | 99.9% | <8.7h downtime/year |
| **DB Connections** | <50% pool | Monitor saturation |
| **Cache Hit Rate** | >70% | Steady-state workload |

---

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────┐
│ 1. Network Layer                         │
│   ├─ WAF (rate limiting, IP blocking)   │
│   └─ DDoS protection                     │
├─────────────────────────────────────────┤
│ 2. TLS/HTTPS                             │
│   ├─ Valid certificates                  │
│   └─ HSTS headers                        │
├─────────────────────────────────────────┤
│ 3. Authentication                        │
│   ├─ OAuth 2.0 (Google)                 │
│   ├─ JWT with HttpOnly cookies          │
│   └─ API keys with scopes               │
├─────────────────────────────────────────┤
│ 4. Authorization                         │
│   ├─ RBAC (admin/editor/reader)         │
│   ├─ Workspace isolation                │
│   └─ API key scope enforcement          │
├─────────────────────────────────────────┤
│ 5. Input Validation                      │
│   ├─ Pydantic models                     │
│   ├─ File type whitelist                │
│   └─ Query length limits                │
├─────────────────────────────────────────┤
│ 6. Rate Limiting                         │
│   ├─ SlowAPI (30/min queries)           │
│   └─ Workspace quotas                   │
├─────────────────────────────────────────┤
│ 7. Data Isolation                        │
│   ├─ Workspace-scoped queries           │
│   └─ User-scoped data                   │
├─────────────────────────────────────────┤
│ 8. Audit Logging                         │
│   ├─ All auth events                     │
│   ├─ Admin operations                    │
│   └─ Billing events                      │
└─────────────────────────────────────────┘
```

---

## Deployment Architectures

### Development (Local)
```
Docker Compose:
- PostgreSQL (single instance)
- Mini-RAG app (1 instance)
- Optional: Redis, Jaeger
```

### Staging
```
Cloud VM (or managed service):
- App: 2 instances behind load balancer
- DB: Managed PostgreSQL (single AZ)
- Cache: Managed Redis
- Monitoring: Grafana Cloud
```

### Production
```
Kubernetes cluster:
- App: 3+ pods (autoscaling)
- DB: Managed PostgreSQL (multi-AZ)
- Cache: Redis cluster
- Storage: S3/Cloud Storage
- Monitoring: Prometheus + Grafana + Alertmanager
- Tracing: Jaeger/Tempo
- Secrets: Vault/Cloud KMS
```

---

**See Also:**
- `docs/guides/DEPLOYMENT_CHECKLIST.md` - Deployment steps
- `docs/guides/PERFORMANCE_TUNING.md` - Optimization guide
- `docs/guides/TROUBLESHOOTING.md` - Common issues

