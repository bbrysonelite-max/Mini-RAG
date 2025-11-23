# Mini-RAG Metrics & Alerting Playbook

This folder contains ready-to-import Grafana and Prometheus resources for operating Mini-RAG in production. Use these assets to monitor latency, ingestion health, quota saturation, background jobs, and upstream dependencies.

## Contents

- `mini-rag-dashboard.json` – Grafana dashboard covering:
  - Ask request latency (p95/p99) and error ratio
  - Ingest throughput + failure breakdown by source
  - Quota usage heatmap (workspace-level)
  - Background job failure trends
  - External dependency errors (Stripe, OpenAI, etc.)
- `mini-rag-alerts.yml` – Prometheus/Alertmanager rules enforcing the agreed SLOs:
  - Ask latency p95 > 3s for 5m
  - Ask error ratio > 2% for 5m
  - Ingest failure rate > 10% for 10m
  - Workspace quota ratio > 90% for 10m
  - Background job failures present for 5m
  - External dependency errors > 3/min for 5m

## Prerequisites

1. **Prometheus scrape** of the Mini-RAG `/metrics` endpoint.
   - Ensure the Prometheus job has network access to the FastAPI server.
   - Confirm metric names (e.g., `ask_request_latency_seconds_bucket`) appear in `curl http://<host>:<port>/metrics`.
2. **Grafana data source** pointing to the Prometheus instance.
3. (Optional) **Alertmanager** integrated with Prometheus for routing alerts.

## Deployment Steps

### 1. Import Grafana Dashboard
1. Open Grafana → **Dashboards** → **Import**.
2. Upload `mini-rag-dashboard.json` or paste its JSON contents.
3. Select the Prometheus data source during import.
4. Verify panels render data; adjust the default time range (dashboard assumes `now-6h`).
5. Update the dashboard UID/title if you want multiple environment variants (e.g., staging vs prod).

### 2. Load Alert Rules
1. Copy `mini-rag-alerts.yml` into your Prometheus rule directory (e.g., `/etc/prometheus/rules/`).
2. Update any environment-specific labels or thresholds:
   - Lower thresholds for staging (more sensitive) or raise for prod depending on baselines.
   - Adjust severity labels to match your Alertmanager routing (`critical`, `warning`, etc.).
3. Reload Prometheus: `promtool check rules mini-rag-alerts.yml` → `curl -XPOST http://<prom-host>/-/reload`.
4. Confirm the rules appear in Prometheus UI → **Status** → **Rules**.
5. Validate alerts by simulating load (e.g., run synthetic ingest to trigger throughput, temporarily block upstream API to simulate dependency errors).

### 3. Wire Alertmanager Notifications
1. Ensure Alertmanager routes `service=mini-rag` alerts to the appropriate channel (PagerDuty, Slack, email).
2. Document escalation paths in your runbook (on-call rotation, incident playbooks).
3. Link alerts back to Grafana by embedding the dashboard URL in Alertmanager annotations if desired.

## Operational Runbook Tips

- **Baseline thresholds**: capture typical p95 latency, ingest throughput, and quota usage after launch. Adjust alerts once real traffic stabilizes.
- **Per-workspace monitoring**: the dashboard uses a `workspace` template variable. For high-cardinality tenants, pre-filter the Prometheus scrape or aggregate by organization to avoid large drop-downs.
- **Background jobs**: combine dashboard insights with the `/api/v1/jobs` endpoint to drill into failing tasks.
- **External dependencies**: extend `external_request_errors_total` with new labels if you add vendors. Mirror the alerts with vendor-specific playbooks (Stripe status page, OpenAI usage caps, etc.).
- **Documentation**: update this README whenever metrics or alert thresholds change; keep the Phase 8 plan in sync.

## Validation Checklist

- [ ] Dashboard imported and panels display data.
- [ ] Alert rules loaded without Prometheus syntax errors (`promtool check rules`).
- [ ] Alerts route to the correct on-call channel.
- [ ] Dashboard/alert links documented in `docs/guides/Phase8_Plan.md` and on-call runbook.
- [ ] Synthetic tests confirm alerts trigger and auto-resolve.
