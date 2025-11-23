# OpenTelemetry Tracing Examples

How to trace requests through Mini-RAG for debugging and performance analysis.

---

## Enable Tracing

```bash
export OTEL_ENABLED=true
export OTEL_SERVICE_NAME="mini-rag-production"
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otel-collector.example.com/v1/traces"
# Optional: auth headers
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer xyz"
```

---

## Trace Anatomy

Every request gets:
- **Request ID** (`X-Request-ID` header)
- **Trace ID** (OpenTelemetry span context)
- **User/Workspace context** (attached to spans)

### Example Trace

```
Request ID: req_1a2b3c4d
Trace ID: 7f3e2a1b9c8d...
├─ ask_endpoint (200ms)
│  ├─ resolve_auth (15ms)
│  ├─ quota_check (8ms)
│  ├─ cache_lookup (2ms) → MISS
│  ├─ retrieve_chunks (120ms)
│  │  ├─ bm25_search (45ms)
│  │  └─ pgvector_search (75ms)
│  └─ generate_answer (55ms)
│     └─ openai_completion (52ms)
└─ cache_set (3ms)
```

---

## View Traces

### Jaeger UI

```bash
# Forward Jaeger UI
kubectl port-forward svc/jaeger-query 16686:16686

# Open http://localhost:16686
# Search by:
# - Service: mini-rag-production
# - Operation: ask_endpoint
# - Tag: workspace_id=...
```

### Grafana Tempo

```promql
# Query traces by request ID
{request_id="req_1a2b3c4d"}

# Find slow requests
{service_name="mini-rag"} | duration > 3s

# Filter by user
{user_id="user-uuid-..."}
```

---

## Correlation IDs

Every log entry includes correlation fields:

```json
{
  "event": "ask.started",
  "request_id": "req_1a2b3c4d",
  "trace_id": "7f3e2a1b9c8d...",
  "span_id": "5a4b3c2d...",
  "user_id": "user-uuid",
  "workspace_id": "workspace-uuid",
  "organization_id": "org-uuid"
}
```

### Search Logs by Trace ID

```bash
# Local logs
grep "trace_id.*7f3e2a1b" logs/rag.log | jq

# Loki/Grafana
{service="mini-rag"} |= "7f3e2a1b" | json
```

---

## Custom Spans

Add custom spans to your code:

```python
from telemetry import tracer

@tracer.start_as_current_span("my_operation")
async def expensive_operation():
    # Your code here
    pass

# Or manual span control
with tracer.start_as_current_span("batch_processing") as span:
    span.set_attribute("batch_size", len(items))
    for item in items:
        process(item)
```

---

## Propagate Context to External Services

Traces automatically propagate to:
- OpenAI API calls (via `extra_headers`)
- Stripe API calls (via `client_reference_id`)
- Internal HTTP calls (via `httpx` client)

### Example: Custom External Call

```python
from correlation import build_observability_headers
import httpx

headers = build_observability_headers()
# Returns: {"X-Request-ID": "...", "traceparent": "..."}

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/data",
        headers=headers
    )
```

---

## Debugging Slow Requests

### 1. Find Slow Traces in Jaeger

```
Service: mini-rag
Min Duration: 3s
Tags: endpoint=/api/v1/ask
```

### 2. Identify Bottleneck

Look for:
- Long DB queries → optimize indexes
- Slow OpenAI calls → cache embeddings
- High BM25 search time → reduce corpus or use pgvector

### 3. Correlate with Logs

```bash
# Get trace ID from Jaeger, then:
grep "trace_id.*<TRACE_ID>" logs/rag.log | jq '.event,.duration_ms'
```

### 4. Compare with Metrics

```promql
# P95 latency by endpoint
histogram_quantile(0.95,
  rate(ask_request_latency_seconds_bucket[5m])
)

# Compare with specific trace duration
```

---

## Common Trace Patterns

### Fast Path (Cache Hit)
```
ask_endpoint (25ms)
├─ resolve_auth (10ms)
├─ cache_lookup (2ms) → HIT ✓
└─ return_cached_result (1ms)
```

### Slow Path (Complex Query)
```
ask_endpoint (4.2s)
├─ resolve_auth (12ms)
├─ cache_lookup (3ms) → MISS
├─ retrieve_chunks (450ms)
│  └─ pgvector_search (445ms) ← BOTTLENECK
├─ generate_answer (3.7s)
│  └─ openai_completion (3.68s) ← BOTTLENECK
└─ cache_set (5ms)
```

**Solution:** Cache embeddings, use smaller model

### Error Trace
```
ask_endpoint (ERROR after 105ms)
├─ resolve_auth (15ms)
├─ quota_check (8ms) → EXCEEDED
└─ raise HTTPException(429)
```

---

## Sampling Configuration

For high-traffic deployments, sample traces:

```bash
# Sample 10% of requests
export OTEL_TRACES_SAMPLER=traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1

# Always sample errors
export OTEL_TRACES_SAMPLER=parentbased_always_on
```

### Smart Sampling

Sample 100% of:
- Errors (status code ≥400)
- Slow requests (>2s)
- Admin operations

Sample 10% of:
- Normal requests

```python
# In telemetry.py
from opentelemetry.sdk.trace.sampling import (
    ParentBasedTraceIdRatio,
    TraceIdRatioBased
)

# Custom sampler (advanced)
class SmartSampler(TraceIdRatioBased):
    def should_sample(self, context, trace_id, name, attributes=None, links=None):
        # Always sample errors
        if attributes and attributes.get("http.status_code", 0) >= 400:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)
        
        # Always sample slow requests
        if attributes and attributes.get("duration_ms", 0) > 2000:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)
        
        # Otherwise, sample 10%
        return super().should_sample(context, trace_id, name, attributes, links)
```

---

## Export Traces to Different Backends

### Jaeger (via OTLP)
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://jaeger:4318"
```

### Grafana Tempo
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://tempo:4318"
```

### Honeycomb
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeycomb.io"
export OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-team=YOUR_API_KEY"
```

### New Relic
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.nr-data.net:4318"
export OTEL_EXPORTER_OTLP_HEADERS="api-key=YOUR_LICENSE_KEY"
```

---

## Testing Tracing Locally

```bash
# Run Jaeger all-in-one
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest

# Enable tracing
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"

# Start Mini-RAG
uvicorn server:app --reload

# Make requests
curl -X POST http://localhost:8000/api/v1/ask \
  -H "X-API-Key: mrag_..." \
  -F "query=test" \
  -F "k=5"

# View traces
open http://localhost:16686
```

---

## Best Practices

1. **Always propagate context** when making external calls
2. **Add meaningful attributes** to spans (user_id, workspace_id, etc.)
3. **Sample intelligently** in production (don't trace every request)
4. **Correlate logs with traces** using request_id + trace_id
5. **Set span status** on errors: `span.set_status(StatusCode.ERROR)`

---

**See Also:**
- `docs/guides/PERFORMANCE_TUNING.md` - Optimize based on trace insights
- `docs/guides/Phase8_Plan.md` - Full observability architecture
- OpenTelemetry Docs: https://opentelemetry.io/docs/

