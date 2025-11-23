## Changelog

### 2025-11-17
- Added automated test suite `test_phase3_auth.py` covering JWT, chunk user IDs, search filtering, and admin role checks.
- Ran test suite (`venv/bin/python3 test_phase3_auth.py`); 6 tests passed, 1 skipped (needs DATABASE_URL for user service).
- Documented Phase 3 completion in `docs/phases/PHASE3_COMPLETE.md` and ensured honest reporting of test status.

### 2025-11-18
- Verified project dependencies and installed missing database drivers (`psycopg[binary]`, `psycopg-pool`).
- Updated `test_phase3_auth.py` to use an in-memory FakeDatabase so `user_service` tests run without a live PostgreSQL instance.
- Ran full test suite (`cd /Users/brentbryson/Desktop/mini-rag && ./venv/bin/python3 test_phase3_auth.py`); **all 7 tests passed** ✅ (no skips or failures) with FakeDatabase fallback standing in for PostgreSQL.
- Hardened Google OAuth environment loading by pointing `auth.py` directly at the repo `.env`, ensuring CLI utilities launched via stdin also register `oauth.google`.
- Documented remaining manual verification items: capture full browser-based OAuth flow evidence and repeat UserService checks against a live PostgreSQL/pgvector stack when available.
- Added `chunk_backup.py` to snapshot `out/chunks.jsonl` before ingestion, dedupe, or delete rewrites; integrated backups into `raglite`, `retrieval`, and `server`.
- Extended `test_rag_pipeline.py` with `test_chunk_backups` to confirm append/rewrite flows produce timestamped backups plus a `backups/latest.jsonl` pointer.
- Updated `docs/guides/QUICK_REFERENCE.md` with a backup recovery playbook (including macOS-friendly restore commands).
- Added `restore_chunk_backup` helper and `raglite restore-backup` CLI subcommand, with automated tests covering full restore workflows.
- Made `raglite.write_jsonl` transactional via copy-on-write staging and expanded tests/docs to reflect the atomic swap behavior.
- Moved planning documents from `project/` to `docs/project/` to tidy the repository root.
- Added versioned REST router at `/api/v1` (legacy `/api/*` routes remain available during transition) and refreshed API metadata.
- Extended `db_schema.sql` with `organizations`, `user_organizations`, `workspaces`, and `workspace_members` tables to support multi-tenant planning.
- User service now provisions default org/workspace memberships; ingestion attaches `workspace_id` to chunk records for future isolation.

### 2025-11-19
- Added `api_keys` table plus helper indexes to `db_schema.sql` to support hashed key storage with user/workspace scoping.
- Introduced `api_key_service.py` for secure key generation, listing, verification, and revocation with SHA-256 hashing.
- Added admin CLI `scripts/manage_api_keys.py` (create/list/revoke) and new regression suite `test_api_keys.py` covering the workflow.
- Implemented API key authentication dependency (`api_key_auth.py`) and updated `/api/v1` routes (ask, ingest, dedupe, sources, admin) to honour scopes alongside JWT.
- Added `test_api_key_auth.py` to ensure header extraction, scope enforcement, and invalid key behaviour; `server.py` now prefers API keys when provided.
- Updated `raglite.py` CLI ingest commands to accept optional `--user-id` and `--workspace-id` flags, mirroring the server-side multi-tenant tagging.
- Added `test_cli_workspace_flags` to `test_rag_pipeline.py` to verify CLI ingestion persists the workspace/user metadata.
- Documented the new CLI flags in `docs/guides/QUICK_REFERENCE.md` with macOS-friendly usage tips.
- Ran integration suite (`cd /Users/brentbryson/Desktop/mini-rag && ./venv/bin/python3 test_rag_pipeline.py`); **all 7 tests passed** ✅ covering workspace isolation, CLI tagging, and backup safety.
- Added `APIKeyAuth` FastAPI dependency wrapper plus defensive logging around audit updates so API key auth degrades gracefully when `touch_last_used` fails.
- Expanded `test_api_key_auth.py` to assert header precedence, dependency round-trips, and resilience when audit writes raise errors.
- Documented FastAPI dependency usage in `docs/guides/QUICK_REFERENCE.md` and re-ran `./venv/bin/python3 test_api_key_auth.py` alongside `./venv/bin/python3 test_phase3_auth.py` to confirm OAuth + API key flows stay green.
- Completed Google OAuth smoke test via `/auth/google`, observed 302 redirect to accounts.google.com, mirrored `.env` to `.env.local` for dotenv resilience, and verified breadcrumbs in `logs/rag.log` capturing the callback URI.
- Added structured `_log_event` helpers, query/ingest JSON logging, and Prometheus metrics (`ask_requests_total`, `ask_request_latency_seconds`, `ingest_operations_total`, `ingest_operation_latency_seconds`) to feed the new UI observability dashboards.
- Warmed the search index on startup so the first `/ask` request avoids cold IO, emitting `index.warm_completed` / `index.warm_failed` breadcrumbs for operations visibility.
- Captured a startup `/ask` baseline sample, recording `ask_request_latency_seconds{outcome="baseline"}` and `ask.baseline_*` events for the performance dashboards.
- Exposed `chunk_records_total` gauge so the UI can track index readiness and current chunk volume.
- Refreshed `docs/guides/QUICK_REFERENCE.md` checklist to reflect delivered security/robustness work and highlight remaining Phase 4/5 gaps.
- Added CORS configuration (env-driven) plus security header middleware (CSP, HSTS, nosniff, etc.) and documented the new settings in the quick reference.

### 2025-11-20
- Added `workspace_quota_settings` + `workspace_usage_counters` tables to `db_schema.sql`, establishing per-workspace chunk and request ceilings with sane defaults.
- Introduced `quota_service.py`, providing daily+per-minute request enforcement, chunk storage checks, and persistence of usage counters; quota breaches now raise HTTP 429 with actionable messages.
- Wired `/ask`, `/api/ingest_urls`, and `/api/ingest_files` to consume quotas (requests recorded up front, chunk deltas enforced after ingestion, JSONL counted per workspace).
- Instrumented Prometheus gauges (`workspace_quota_usage`, `workspace_quota_ratio`) and log-based alerts (`quota.threshold`) so on-call teams can graph tenant utilization and page before hard caps hit.
- Created `test_quota_service.py` covering default settings, chunk cap enforcement, per-day request ceilings, and per-minute throttling via frozen time windows.
- Updated `docs/guides/QUICK_REFERENCE.md` (Commercial Features + Backup sections) to note workspace quotas, how to adjust settings via SQL, and where Prometheus metrics surface per-tenant usage.
- Logged the Phase 5 Workspace Quotas plan/results in `tasks/todo.md`, marking P5-B1 through P5-B3 complete with notes on the new gauges and alert thresholds.
- Expanded `organizations` with Stripe billing metadata, introduced `organization_billing_events`, and created `billing_service.py` to manage Stripe checkout, portal sessions, and webhook processing.
- Added `/api/billing/checkout`, `/api/billing/portal`, and `/api/billing/webhook` endpoints (plus `api_v1` aliases) so admins can launch Stripe Checkout/Portal while webhooks update `billing_status` + Stripe IDs.
- Implemented `_require_billing_active` to block `/api/ingest_urls` + `/api/ingest_files` when trials expire or subscriptions lapse; `test_billing_guard.py` covers the guard rails.
- Documented billing environment variables, endpoints, and ingestion gating in `docs/guides/QUICK_REFERENCE.md`, and captured the Phase 5C review + checklist updates in `tasks/todo.md`.
- Added `docs/guides/BILLING_AND_API.md`, a customer-facing onboarding guide covering Stripe setup, new env vars, sample curl/Postman calls, and ingestion blocking behavior.
- Published `clients/sdk.py` (minimal Python client) and `docs/postman/mini-rag.postman_collection.json` so integrators can script the API quickly; `tests/test_api_contract.py` ensures core routes stay wired.
- Delivered Phase 6 UI shell: `frontend/index.html` now renders a persistent header, breadcrumb trail, modal-close behavior, ask loading indicator, ingest toasts, and empty states; added `docs/guides/UI_NAVIGATION.md` plus Quick Reference updates.
- Added GitHub Actions pipeline (`.github/workflows/ci.yml`) running backend pytest selection and React build placeholder, plus `docs/infra/CI_SETUP.md` capturing required secrets and future enhancements.
- Added admin endpoints (`/api/v1/admin/workspaces`, `/api/v1/admin/billing`, `PATCH /api/v1/admin/billing/{org_id}`) guarded by admin scope to surface workspace/billing metadata for ops tooling.
- Added optional OpenTelemetry/correlation ID support (`telemetry.py`, `correlation.py`, `logging_utils` updates, README instructions) so deployments can emit structured logs/traces with request IDs and ship them to an OTLP collector.

### 2025-11-21
- Implemented per-request tenant context propagation by extending `correlation.py` with user/workspace/organization contextvars and resetting them per ASGI request.
- Updated `_resolve_auth_context` to populate the correlation context (user/workspace/org) so downstream logs, metrics, and OTEL spans automatically inherit tenant metadata.
- Expanded `_log_event` and `logging_utils.JsonFormatter` to auto-enrich every structured log with `request_id`, `trace_id`, `span_id`, `user_id`, `workspace_id`, and `organization_id`, even when individual call sites omit those fields.
- Documented the enriched schema plus a concrete JSON sample in `docs/guides/Phase8_Plan.md`, and refreshed `tasks/todo.md` to mark P8-O1-2 complete while focusing Step 3 on schema verification.
- Ran targeted regression (`DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag_brain STRIPE_API_KEY=fake STRIPE_WEBHOOK_SECRET=whsec_test ./venv/bin/python3 -m pytest tests/test_admin_api.py`) to ensure admin routes remain stable with the new middleware.
- Added `build_observability_headers` helper and now forward `X-Request-ID` + `traceparent` to outbound `httpx` healthcheck pings, OAuth profile lookups, and OpenAI SDK calls via `with_options(extra_headers=...)`.
- Stripe checkout and customer creation requests now embed the backend `request_id` inside metadata/client reference fields so Stripe dashboards can pivot on the same identifier as our logs/traces.
- Updated `docs/guides/Phase8_Plan.md` Step 4 notes with the propagation changes and re-ran the admin API pytest selection to confirm no regressions.
- Authored Phase 8 observability runbook (Step 5) detailing retention policies, dashboard queries, on-call SOP, access control requirements, and troubleshooting guidance in `docs/guides/Phase8_Plan.md`; recorded completion in `tasks/todo.md`.
- Kicked off P8-O2 by cataloging existing Prometheus metrics, highlighting latency/throughput/alert gaps, and capturing desired alert conditions in `docs/guides/Phase8_Plan.md`; `tasks/todo.md` now points to instrumentation design as the next step.
- Completed P8-O2 instrumentation strategy: defined histogram bucket plans, error counters, throughput/queue gauges, quota/health alerts, label hygiene, and dashboard rollout in `docs/guides/Phase8_Plan.md`; advanced the todo list to implementation.
- Implemented P8-O2 instrumentation: tightened ask/ingest latency histograms, added status-code labels to request counters, introduced `ingest_processed_chunks_total`, `quota_exceeded_total`, `external_request_errors_total`, instrumented ingestion flows with the new helpers, and incremented Stripe failure counters; documented the changes in `docs/guides/Phase8_Plan.md` Step 3 and closed out the todo item.

