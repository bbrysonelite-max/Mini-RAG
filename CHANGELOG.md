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


