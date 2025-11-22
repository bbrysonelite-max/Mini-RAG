# Phase 8 – Observability & Scaling Blueprint

## Objective
Deliver enterprise-grade observability, background processing, and compliance controls so Mini-RAG can serve production workloads with confidence.

## Proposed Tracks

### P8-O1: Centralized Logging & Tracing
- Adopt OpenTelemetry / structured logging.
- Emit correlation IDs and per-request metadata.
- Ship logs to a centralized stack (ELK, Datadog, etc.).

#### Current State & Gaps (Step 1)
- `logging_utils.py` emits JSON but lacks standardized fields (no trace/span IDs, tenant context is ad-hoc).
- Request timing is available via `RequestTimer`, yet those metrics are only written to logs/Prometheus without linkage to downstream calls.
- No correlation ID header is propagated through FastAPI handlers, CLI ingestion, or admin APIs.
- There's no OTLP exporter or log shipping strategy—operators must tail local files manually.

#### Proposed Design
- **Instrumentation:** Integrate `opentelemetry-sdk` + `opentelemetry-instrumentation-fastapi` to produce traces for HTTP requests. Use W3C Trace Context headers (`traceparent`) and expose them via middleware for reuse in logs.
- **Correlation IDs:** Introduce an ASGI middleware that:
  1. Reads `X-Request-ID` or generates a UUIDv4.
  2. Stores it in `contextvars` so logging calls and downstream tasks can access the same value.
  3. Writes `X-Request-ID` (and `traceparent`) back to the response for client-side debugging.
- **Structured Schema:** Extend `logging_utils` to include:
  - `trace_id`, `span_id`, `request_id`
  - `user_id`, `workspace_id`, `organization_id`
  - `route`, `method`, `status_code`, `latency_ms`
  - Optional `billing_status`, `quota_context`
- **Exporters:** Start with OTLP/HTTP pointing at a configurable collector URL. For local dev, default to console logging; in production, point to Datadog or OpenTelemetry Collector.
- **Dashboards:** Document how to visualize traces (e.g., Jaeger/Grafana Tempo) and how to correlate them with Prometheus metrics (using the same trace IDs).

#### Step 2 Progress (Middleware & Exporter)
- Added `correlation.py` middleware that normalizes `X-Request-ID`, stores request/user/workspace/org IDs in `contextvars`, and propagates headers back to clients.
- Created `telemetry.py` to centralize OTEL configuration (console exporter by default, OTLP configurable via `OTEL_EXPORTER_OTLP_ENDPOINT` + `OTEL_EXPORTER_OTLP_HEADERS`).
- Updated `server.py` to:
  - Toggle OTEL via `OTEL_ENABLED`.
  - Register `CorrelationIdMiddleware` + FastAPI instrumentation.
  - Auto-enrich `_log_event` with request, tenant, and trace identifiers.
- Extended `README.md` and `CHANGELOG.md` with enablement instructions and troubleshooting notes.

#### Step 3 – Log Schema & Samples
- **Fields (baseline):**
  - `timestamp`, `level`, `logger`, `message`, `event`
  - `request_id`, `trace_id`, `span_id`
  - `user_id`, `workspace_id`, `organization_id`
  - `metric`, `ratio`, or other event-specific payload
- **Optional extensions:** `billing_status`, `quota_context`, `route`, `method`, `status_code`, `duration_ms`.
- **Sample payload:**

```
{"timestamp":"2025-11-21T08:15:31.123Z","level":"INFO","logger":"rag","message":"quota.threshold","event":"quota.threshold","request_id":"9052f1c3-1e77-4e85-9e16-5d7c2c6f4e53","trace_id":"40c8d3b0e2a44eeaa61d1c395cd5a0b2","span_id":"1b9c0d7e3f1a45c2","user_id":"usr_123","workspace_id":"wsp_789","organization_id":"org_456","metric":"chunk_storage","ratio":0.92}
```

#### Step 4 – Downstream Propagation
- Added `build_observability_headers` helper to emit `X-Request-ID` + W3C `traceparent` based on the active span/context.
- Healthcheck/webhook `httpx` calls now attach those headers and emit `_log_event` breadcrumbs on success/failure.
- OAuth Google profile fetch uses the same helper so vendor logs correlate user-info lookups with backend requests.
- OpenAI SDK usage leverages `client.with_options(extra_headers=...)` to forward observability headers during chat + embedding calls.
- Stripe checkout/customer creation include the request ID inside `metadata` and `client_reference_id`, aligning billing events with application logs.

#### Step 5 – Operational Runbook
- **Retention & Storage**
  - Default retention: keep JSON console + `logs/rag.log` for 14 days locally; ship OTLP traces/logs to external collector with 30-day retention.
  - Rotate file handler at 10 MB × 5 backups (configurable via `logging_utils.configure_logging`); document overrides in `LOG_ROTATION_MAX_BYTES`, `LOG_ROTATION_BACKUPS`.
  - Collector guidance: deploy OpenTelemetry Collector → S3/Datadog/ELK; enforce bucket lifecycle policies aligned with customer contracts.
- **Dashboards & Queries**
  - Prometheus/Grafana: import dashboards for `ask_request_latency_seconds` (p50/p95/p99), `workspace_quota_ratio`, `healthcheck.ping_*` event counts.
  - LogQL examples (Loki): `event="quota.threshold" | unwrap ratio | avg()`; `event="billing.blocked" | json | count_over_time(...)`.
  - Trace UI (Jaeger/Tempo): filter by `service.name="mini-rag"` and correlate using `request_id` attribute.
- **On-call SOP**
  - Every incident ticket must include `request_id` (from client toast or API response) to cross-reference logs/traces quickly.
  - Escalation checklist: 1) check `/metrics` for error spikes; 2) review `healthcheck.ping_failed`; 3) inspect traces for external latency (Stripe/OpenAI).
  - Provide `scripts/oncall/log_sample.sh <request_id>` (TODO) to fetch representative log lines when SSH access is available.
- **Access Controls**
  - Restrict OTLP collector credentials via `OTEL_EXPORTER_OTLP_HEADERS`; rotate monthly and store in secrets manager.
  - Logs shipped to central storage must be tagged with tenant identifiers and comply with deletion/export requests.
  - Document audit trail for who can access observability dashboards; require SSO in production environments.
- **Troubleshooting**
  - If traces are missing, validate `OTEL_ENABLED=true` and collector connectivity; check exporter warnings at startup.
  - For mismatched request IDs, ensure reverse proxies preserve `X-Request-ID` and are configured to fall back to backend-generated UUIDs.
  - Stripe/OpenAI correlation: verify metadata contains `request_id`; compare timestamps between vendor dashboard and internal logs.

> Next steps: finish documenting downstream propagation + operational runbooks after verifying the enriched schema in real OTLP collectors.

### P8-O2: Metrics & Alerting
- Extend Prometheus coverage (p95/p99 latencies, ingestion throughput, queue depth, quota saturation).
- Provide Grafana dashboards + Alertmanager rules for on-call handoff.

#### Step 1 – Metrics Inventory & Gaps
- **Current instrumentation:** `ask_requests_total`, `ask_request_latency_seconds` (histogram), `ingest_operations_total`, `ingest_operation_latency_seconds`, `chunk_records_total`, `workspace_quota_usage`, `workspace_quota_ratio`, and event breadcrumbs (e.g., `quota.threshold`, `healthcheck.ping_*`).
- **Coverage gaps:**
  - Missing high-percentile exports (p95/p99) for ask/ingest latency and no histogram buckets tuned for sub-second / multi-second ranges.
  - No counters for error classifications (4xx/5xx), ingestion failures, or Stripe/OpenAI dependency errors.
  - Lacks throughput metrics (chunks ingested per minute, embeddings queued/processed) and queue depth placeholders for future background workers.
  - Quota gauges expose absolute numbers but we do not alert on saturation >90% or sustained 429 responses.
  - No dashboards or Alertmanager rules are defined; `/metrics` is exposed but not scraped by default.
- **Desired alerts & dashboards:**
  - Latency SLO: alert when `ask` p95 > 3s for 5 minutes, or error ratio >2%.
  - Ingestion health: alert on sustained ingest failure counters or billing guard 402 spikes.
  - Quota pressure: alert when `workspace_quota_ratio` > 0.9 for any workspace for >10 minutes.
  - Healthcheck: alert if `healthcheck.ping_failed` fires consecutively or `/metrics` scrape fails.

> Outcome: Step 1 captured instrumentation gaps; proceed to Step 2 to design concrete metric additions and alert thresholds.

#### Step 2 – Instrumentation Strategy
- **Latency histograms:** add `ask_request_latency_seconds` buckets `[0.1, 0.25, 0.5, 1, 2.5, 5, 10]` and mirror for ingest operations; expose Prometheus `histogram_quantile` (p95/p99) via Grafana queries.
- **Error counters:** introduce `ask_requests_total{outcome="error",code="5xx"}` & `ingest_operations_total{outcome="error",code="4xx/5xx"}` with `code` and `source` labels to drive error-rate alerts.
- **Throughput gauges:** track `ingest_processed_chunks_total` (counter) and `embedding_queue_depth` (gauge placeholder using async queue length once background workers arrive); short-term use simple counters with no queue.
- **Quota/utilization alerts:** compute `workspace_quota_ratio` > 0.9 triggers; add `quota_exceeded_total` counter for 429 responses, enabling rate-based alerts.
- **External dependency metrics:** add counters for Stripe webhook failures and OpenAI API failures (`external_request_errors_total{service="stripe"|"openai"}`), plus latency histograms if needed.
- **Alert thresholds (starting point):**
  - **Latency:** `histogram_quantile(0.95, sum(rate(ask_request_latency_seconds_bucket[5m])) by (le)) > 3`.
  - **Error ratio:** `sum(rate(ask_requests_total{outcome="error"}[5m])) / sum(rate(ask_requests_total[5m])) > 0.02`.
  - **Quota saturation:** `max_over_time(workspace_quota_ratio[10m]) > 0.9`.
  - **Healthcheck:** `increase(healthcheck_ping_failed_total[5m]) > 0`.
- **Label hygiene:** keep label cardinality low (`workspace_id` only where necessary; aggregate by organization for alerts).
- **Dashboard plan:** create Grafana dashboards with latency/error panels, ingest throughput, quota saturation table, and dependency status; link to alert rules stored under `docs/infra/metrics_alerts/`.

#### Step 3 – Metrics & Alerts Implemented
- Updated existing histograms (`ask_request_latency_seconds`, `ingest_operation_latency_seconds`) with fine-grained buckets for accurate p95/p99 computation.
- Extended `ask_requests_total` and `ingest_operations_total` to include `status_code` labels, plus a helper `_record_ingest_event` ensuring consistent labeling across successes/skip/failure paths.
- Added counters/gauges:
  - `ingest_processed_chunks_total{source}` to track throughput per ingestion type.
  - `quota_exceeded_total{workspace_id,metric}` incremented when `QuotaService` rejects requests.
  - `external_request_errors_total{service,operation}` currently wired for Stripe checkout/portal/webhook failures (OpenAI wiring pending).
- Instrumented ingestion flows to increment counters with 200/400/500-class status codes, record processed chunk counts, and capture fallback outcomes.
- Stripe API error paths now bump the external error counter, complementing existing log breadcrumbs.
- Next steps: expose Alertmanager rule templates + Grafana dashboards under `docs/infra/` and extend external-error coverage to OpenAI once background workers land.

### P8-Q1: Background Workers
- Introduce a job queue (Celery/RQ/Temporal) for asynchronous embedding, large ingests, and scheduled re-indexing.
- Add retry policies, dead-letter handling, and queue metrics.

### P8-S1: Security Posture
- Harden CSP/security headers, add dependency/container scanning to CI.
- Explore SSO/SAML and audit-ready access logs.

### P8-C1: Compliance & Data Retention
- Design export/delete workflows, retention policies, and encrypted backups.
- Ensure audit logs capture admin actions and billing events.

### Phase 8 – Background Processing

- Introduced `background_queue.BackgroundTaskQueue` (asyncio-based) to serialize maintenance jobs.
- Enabled optional queueing for `/dedupe` and `/rebuild` when `BACKGROUND_JOBS_ENABLED=true`; synchronous fallback remains the default.
- Added `/api/v1/jobs` endpoint for operators to inspect recent job history.
- Prometheus counters/histograms capture job submissions, outcomes, and durations.

## Next Steps
1. Confirm which track to tackle first (e.g., P8-O1 Logging).
2. Break it into concrete tasks (schema updates, code changes, docs, tests).
3. Iterate through each track with the same “plan → execute → document” cadence used in previous phases.

> This blueprint is a living doc—update it as priorities evolve or new enterprise requirements surface.

