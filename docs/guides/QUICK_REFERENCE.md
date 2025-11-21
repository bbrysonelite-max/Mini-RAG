# Quick Reference: Making RAG Commercial-Ready

## 🚨 Critical Issues (Fix Immediately)

| Issue | Severity | Impact | Fix Time |
|-------|----------|--------|----------|
| No Authentication | 🔴 CRITICAL | Anyone can access/modify data | 1-2 days |
| File Upload Vulnerabilities | 🔴 CRITICAL | Path traversal, malicious files | 1 day |
| Command Injection | 🔴 CRITICAL | Remote code execution | 1 day |
| No Input Validation | 🟠 HIGH | DoS, data corruption | 2 days |
| Poor Error Handling | 🟠 HIGH | System crashes, data loss | 2 days |
| No Rate Limiting | 🟠 HIGH | DoS attacks | 1 day |

## ✅ Quick Wins (Easy Improvements)

| Task | Status | Notes |
|------|--------|-------|
| Add file size limits | ✅ | `MAX_FILE_SIZE` enforced across ingest endpoints |
| Sanitize filenames | ✅ | `generate_safe_filename` + path stripping live |
| Add request timeouts | ✅ | `/ask` guarded by `asyncio.wait_for(timeout=30.0)` |
| Improve error messages | ✅ | Custom exception handler returns safe responses; full trace logged |
| Add health check | ✅ | `/health` reports index + DB status |

## 📋 Checklist for Commercial Readiness

### Security
- [x] Authentication & Authorization (JWT/OAuth + API keys)
- [x] Input validation (Pydantic models on ingest/query payloads)
- [x] File upload security (sanitization, size limits, hashing)
- [x] URL validation (YouTube extractor + strict patterns)
- [x] Rate limiting (SlowAPI guards across write/read endpoints)
- [x] CORS configuration (`CORS_ALLOW_ORIGINS` env with sane defaults)
- [x] XSS prevention (CSP + sanitized JSON error payloads)
- [x] Error message sanitization (custom handlers, structured logging)
- [x] Security headers (CSP, HSTS, X-Content-Type-Options, etc.)

### Robustness
- [x] Comprehensive error handling (domain-specific + fallback handlers)
- [x] Request timeouts (query + ingest timers)
- [x] File size limits
- [ ] Thread-safe operations (review DB + file locks)
- [x] Backup system (automatic snapshots + restore CLI)
- [x] Recovery mechanisms (copy-on-write & restore helper)
- [ ] Resource limits (CPU/memory quotas, concurrency caps)
- [ ] Graceful degradation (non-critical services fallback)

#### Backup Recovery Playbook
- All chunk mutations (CLI ingest, `/api/ingest_files`, `/api/dedupe`, `/api/sources/{id}` deletes) snapshot the live file to `backups/`.
- Snapshots are stored as `backups/chunks-<timestamp>.jsonl` and mirrored to `backups/latest.jsonl` for quick restores.
- On macOS you can restore via Terminal with `cp backups/latest.jsonl out/chunks.jsonl` (or press `Cmd` + `Shift` + `G` in Finder to jump to the project folder before copying).
- Prefer the automated flow: `./venv/bin/python raglite.py restore-backup --chunks out/chunks.jsonl` restores from the latest snapshot; add `--backup backups/chunks-<timestamp>.jsonl` to pick a specific file.
- Chunk writes use copy-on-write staging + `os.replace`, so ingestion either keeps the old file or atomically swaps in the fully-written version.
- Keep older snapshots for audits and prune with a retention policy (for example, `find backups -type f -mtime +7 -delete`).
- CLI ingest commands (`ingest-docs`, `ingest-transcript`, `ingest-youtube`) accept optional `--user-id` and `--workspace-id` flags so you can tag chunks from Terminal. Example: `./venv/bin/python raglite.py ingest-docs --path ./notes/intro.md --out out/chunks.jsonl --user-id $(uuidgen) --workspace-id default-workspace` (use `Cmd` + `Shift` + `.` in Finder to reveal hidden folders before copying paths).
- **API key issuance:** Admins can mint keys via `./venv/bin/python scripts/manage_api_keys.py create --user <uuid> [--workspace <uuid>] [--scope read --scope write]`. The command prints the plaintext **once**—store it immediately. List keys with `list` and revoke via `revoke --id <key_uuid>`.
- **API key authentication:** Clients can send `X-API-Key: <token>` (or `Authorization: ApiKey <token>`) when calling `/api/v1/*`. Scopes are enforced (`read`, `write`, `admin`) so ingest/delete/rebuild require `write` and admin endpoints require `admin`.
- **API key dependency:** FastAPI routes can depend on `APIKeyAuth` to guarantee scope checks. Example: `@router.post("/ingest", dependencies=[Depends(APIKeyAuth(("write",)))])` or inject directly: `async def ingest(principal: APIKeyPrincipal = Depends(APIKeyAuth(("write",))))`.
- **Metrics:** `/metrics` exposes `ask_requests_total`, `ask_request_latency_seconds` (including a startup `baseline` sample), `ingest_operations_total{source, outcome}`, `ingest_operation_latency_seconds{source, outcome}`, and `chunk_records_total` so dashboards can chart query volume, tail latencies, ingest throughput/failures, and index readiness in real time.
- **Quota metrics & alerts:** Workspace quotas now export `workspace_quota_usage{workspace_id,metric}` (requests_today, requests_current_minute, chunks_today, chunk_total) and `workspace_quota_ratio{workspace_id,metric}` (requests_per_day, requests_per_minute, chunk_storage). When ratios exceed 0.9 the server emits `quota.threshold` logs—wire Prometheus alerts on these gauges to page ops before hard 429s trigger.
- **Billing integration:** Provide `STRIPE_API_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`, and `STRIPE_PORTAL_RETURN_URL` to enable `/api/v1/billing/checkout`, `/api/v1/billing/portal`, and `/api/v1/billing/webhook` (legacy `/api/billing/*` aliases remain). Checkout metadata carries `organization_id` so webhooks update `organizations.billing_status`.
- **Ingestion gating:** `/api/ingest_urls` and `/api/ingest_files` call `_require_billing_active`. Trials (`billing_status=trialing`) work until `trial_ends_at`; `past_due`, `canceled`, or expired subscriptions yield HTTP 402 with `billing.blocked` logs, preventing new content uploads while queries remain available.
- **UI navigation:** The web client now features a persistent header, breadcrumb trail, toast notifications, and ESC-dismissable chunk modal. See `docs/guides/UI_NAVIGATION.md` for flows and future enhancements.
- **Admin APIs:** Use `/api/v1/admin/workspaces` to list tenants and `/api/v1/admin/billing` + `PATCH /api/v1/admin/billing/{org_id}` to inspect or override billing states (requires admin scope/API key).
- **Security headers & CORS:** `CORS_ALLOW_ORIGINS` controls allowed origins (default `*`); `CONTENT_SECURITY_POLICY` overrides the default CSP. Middleware enforces HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and XSS protection headers.

### Usability
- [x] Navigation shell (Ask/Sources/Ingest/Admin + breadcrumb)
- [x] Loading states (Ask spinner, ingest toasts/progress)
- [x] Progress indicators (ingest progress bar + history)
- [ ] Onboarding/tutorial
- [ ] Help documentation
- [ ] Keyboard shortcuts
- [ ] Search improvements
- [ ] React UI migration (see `docs/guides/REACT_MIGRATION.md`)

### Commercial Features
- [ ] Multi-tenancy
- [ ] User management
- [x] Usage quotas (workspace-level request + storage limits)
- [x] Billing integration (Stripe checkout/portal + webhooks)
- [x] API versioning (`/api/v1` router live)
- [ ] API documentation
- [x] Monitoring & logging (Prometheus metrics, structured logs, baselines)
- [ ] Analytics

- `/api/v1` REST endpoints now mirror existing `/api/*` routes; authenticate with JWT cookies or API keys.
- API key storage uses hashed records in the new `api_keys` table with per-key scopes and revocation timestamps; use the manage script above for operations.
- **Workspace quotas:** `workspace_quota_settings` controls `chunk_limit`, `request_limit_per_day`, and `request_limit_per_minute`. `/ask`, `/api/ingest_urls`, and `/api/ingest_files` call into `QuotaService`, which tracks usage via `workspace_usage_counters`. Adjust limits via SQL (e.g., `INSERT ... ON CONFLICT DO UPDATE`) and watch Prometheus gauges to spot near-capacity tenants.

### Infrastructure
- [ ] Database (PostgreSQL)
- [ ] Vector database (Pinecone/Weaviate)
- [ ] Caching (Redis)
- [ ] Queue system (Celery)
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Environment config
- [ ] Secrets management

### Testing
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests
- [ ] E2E tests
- [ ] Load testing
- [ ] Security testing

### Documentation
- [ ] User guide
- [ ] API documentation
- [ ] Developer guide
- [ ] Deployment guide
- [ ] Architecture docs

### Compliance
- [ ] Privacy policy
- [ ] Terms of service
- [ ] GDPR compliance
- [ ] Data retention policies
- [ ] Security certifications

## 🎯 MVP vs Commercial Feature Comparison

| Feature | MVP | Commercial |
|---------|-----|------------|
| Authentication | Basic API key | Full OAuth/JWT with RBAC |
| Multi-tenancy | Single user | Full multi-tenant |
| Database | JSONL files | PostgreSQL + Vector DB |
| Monitoring | Basic logs | Full APM + alerts |
| Scaling | Single server | Horizontal scaling |
| Testing | Manual | Automated (80%+ coverage) |
| Documentation | README | Comprehensive docs |
| Support | Email | Ticket system + SLA |

## 💰 Cost-Benefit Analysis

### Development Investment
- **Security fixes:** 2-3 weeks ($10K-20K)
- **Robustness:** 2-3 weeks ($10K-20K)
- **Multi-tenancy:** 4-6 weeks ($20K-40K)
- **Infrastructure:** 2-3 weeks ($10K-20K)
- **Testing:** 2-3 weeks ($10K-20K)
- **Documentation:** 1-2 weeks ($5K-10K)
- **Total:** 13-20 weeks ($65K-130K)

### Revenue Potential
- **SaaS Model:** $29-99/month per user
- **100 users:** $2,900-9,900/month
- **1,000 users:** $29,000-99,000/month
- **Break-even:** 6-12 months (with 100-200 users)

## 🚀 Recommended Next Steps

1. **This Week:**
   - Implement file upload security fixes
   - Add input validation
   - Fix command injection vulnerabilities

2. **Next 2 Weeks:**
   - Add authentication
   - Improve error handling
   - Add rate limiting

3. **Next Month:**
   - Set up monitoring
   - Add database
   - Implement multi-tenancy basics

4. **Next 3 Months:**
   - Full testing suite
   - Documentation
   - Security audit
   - Beta launch

## 📚 Key Documents

1. **docs/notes/COMMERCIAL_VIABILITY_ANALYSIS.md** - Full analysis
2. **docs/guides/CRITICAL_FIXES_GUIDE.md** - Code-level fixes
3. **This document** - Quick reference

## 🔗 Useful Resources

- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **Pydantic Validation:** https://docs.pydantic.dev/
- **Rate Limiting:** https://slowapi.readthedocs.io/

---

**Bottom Line:** The codebase has a solid foundation but needs 3-6 months of focused development to be commercially viable. Start with security fixes immediately.

