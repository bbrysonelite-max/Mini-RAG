# Development Roadmap: Mini-RAG to Commercial Product

This document tracks the step-by-step development of Mini-RAG from prototype to commercial software.

## Current Status: ✅ Prototype Complete

- [x] Core RAG functionality
- [x] Web UI with document browser
- [x] Document ingestion (files, YouTube, transcripts)
- [x] Basic error handling
- [x] Status messages for user feedback
- [x] Repository on GitHub

---

## Phase 1: Testing & Validation (1-2 weeks)

**Goal:** Use the system in real scenarios and identify issues

- [ ] Test with various document types
- [ ] Test with multiple YouTube videos
- [ ] Document bugs and issues
- [ ] Gather feature requests
- [ ] Performance testing
- [ ] User experience testing

**Notes:**
- Use the system daily
- Keep a log of issues encountered
- Identify most common use cases

---

## Phase 2: Critical Security Fixes (2-3 weeks) 🔴 HIGH PRIORITY

**Goal:** Make the system secure enough for any production use

### Week 1: File Upload Security ✅
- [x] Sanitize filenames (prevent path traversal)
- [x] Add file size limits (100MB max)
- [x] Validate file types (whitelist)
- [x] Generate safe filenames (UUID-based)
- [x] Add file scanning/malware checks (optional - skipped, not needed)

### Week 2: Input Validation ✅
- [x] Add Pydantic models for all API endpoints
- [x] Validate query length (max 5000 chars)
- [x] Validate `k` parameter (1-100 range)
- [x] URL validation for YouTube ingestion
- [x] Language code validation

### Week 3: Error Handling & Rate Limiting ✅
- [x] Replace bare `except` clauses with specific exceptions
- [x] Add structured error logging
- [x] Implement rate limiting (30 req/min for queries, 10/hour for uploads)
- [x] Add request timeouts
- [x] Sanitize error messages (don't expose internal paths)

**Reference:** See `docs/guides/CRITICAL_FIXES_GUIDE.md` for code examples

---

## Phase 3: Authentication & User Management (1-2 weeks) ✅

**Goal:** Add basic authentication and user accounts

- [x] Choose auth method (JWT or API keys) - Google OAuth + JWT
- [x] Implement user registration/login - Google OAuth
- [x] Add user sessions - JWT tokens with 7-day expiry
- [x] Protect API endpoints - All sensitive endpoints require auth
- [x] Add user-specific data isolation - Chunks filtered by user_id
- [x] Create admin user role - First user is admin, admin endpoints added

**Options:**
- Simple: API keys per user
- Standard: JWT tokens
- Advanced: OAuth integration

---

## Phase 4: Robustness & Polish (2-3 weeks) ✅

**Goal:** Make the system production-ready and reliable

### Error Recovery ✅
- [x] Add backup system for chunks.jsonl (timestamped backups + restore CLI)
- [x] Implement transaction-like operations (copy-on-write staging)
- [x] Add rollback capability (`raglite restore-backup`)
- [x] Health check endpoint (`/health` with DB + index status)
- [x] Automatic recovery mechanisms (backup before every mutation)

### Monitoring & Logging ✅
- [x] Structured logging (JSON format with OpenTelemetry integration)
- [x] Error tracking (`_log_event` with correlation IDs)
- [x] Usage analytics (Prometheus metrics for ask/ingest/quota)
- [x] Performance monitoring (latency histograms, error counters)
- [x] Log rotation (rotating file handler in `logging_utils`)

### Performance ✅
- [x] Add caching layer (in-memory BM25 index + warm-up on startup)
- [x] Optimize index building (async pipeline + cached reads)
- [x] Add database for metadata (PostgreSQL with async pooling)
- [x] Implement connection pooling (`psycopg-pool` for DB)
- [x] Add request queuing for large operations (background job queue for rebuild/dedupe)

### User Experience 🚧
- [x] Keyboard shortcuts (Cmd+Enter to ask, Cmd+K focus, ESC to close)
- [ ] Better onboarding/tutorial
- [ ] Export functionality
- [ ] Search improvements (autocomplete, history)
- [x] Mobile responsiveness improvements (responsive grid + nav)

---

## Phase 5: Commercial Features (Ongoing) ✅

**Goal:** Add features needed for commercial deployment

### Multi-Tenancy ✅
- [x] Organization/workspace support (schema + default membership)
- [x] Data isolation per tenant (workspace_id filtering)
- [x] Usage quotas and limits (QuotaService with per-workspace ceilings)
- [x] Billing integration (Stripe checkout/portal/webhooks)
- [x] Subscription management (trial/active/past_due states)

### API & Integration ✅
- [x] RESTful API with versioning (`/api/v1/` router live)
- [x] API documentation (OpenAPI/Swagger at `/docs`)
- [x] API keys for programmatic access (hashed storage + scope enforcement)
- [x] Webhooks for events (Stripe billing webhooks)
- [x] SDKs for popular languages (Python SDK in `clients/sdk.py`)

### Infrastructure 🚧
- [x] Docker containerization (`Dockerfile` + `docker-compose.yml`)
- [ ] Kubernetes deployment configs
- [x] CI/CD pipeline (GitHub Actions with pytest + build checks)
- [x] Environment configuration management (`env.template` + validation)
- [x] Secrets management (startup checks for placeholders)
- [ ] Horizontal scaling support (stateless FastAPI ready, needs load balancer)

### Documentation 🚧
- [x] User documentation (`docs/guides/QUICK_REFERENCE.md`, `BILLING_AND_API.md`)
- [x] API documentation (OpenAPI at `/docs`, Postman collection)
- [ ] Developer guide
- [x] Deployment guide (Docker instructions in README)
- [x] Architecture documentation (Phase completion docs)

### Compliance & Legal ⚠️
- [ ] Privacy policy
- [ ] Terms of service
- [x] GDPR compliance features (audit logging, user-scoped data)
- [ ] Data retention policies
- [ ] Security certifications (future)

---

## Phase 6: Scale & Enterprise (Future)

**Goal:** Support enterprise customers

- [ ] Distributed search (Elasticsearch/Pinecone)
- [ ] Advanced analytics
- [ ] White-label options
- [ ] On-premise deployment
- [ ] Custom integrations
- [ ] Enterprise support

---

## Progress Tracking

### Completed ✅
- Initial prototype
- Web UI with browser
- Document ingestion
- Status messages
- Error feedback
- **Phase 2:** Critical Security Fixes (file upload security, input validation, error handling, rate limiting, timeouts)
- **Phase 3:** Authentication & User Management (Google OAuth, user database, endpoint protection, data isolation, admin role)
- **Phase 4:** Robustness & Polish (backup system, monitoring, PostgreSQL, connection pooling, background jobs)
- **Phase 5:** Commercial Features (multi-tenancy, quotas, billing, API keys, versioned API, Docker, CI/CD)

### In Progress 🚧
- Phase 5: Documentation refinement (developer guide, retention policies)
- Phase 6: UI/UX Polish (React migration, legacy UI normalization)
- Phase 7: Observability (Grafana dashboards deployed, alert tuning)

### Next Up 📋
- Phase 6: UI/UX completion (React parity, onboarding flows)
- Phase 8: Horizontal scaling (K8s configs, load testing)

### Blocked ⛔
- None

---

## Notes & Decisions

### Technology Choices ✅
- **Backend:** FastAPI (Python) with async/await
- **Frontend:** Vanilla JavaScript (legacy) + React (new shell in `frontend-react/`)
- **Database:** PostgreSQL 15+ with pgvector extension
- **Search:** BM25 + hybrid vector search (OpenAI/Anthropic embeddings)
- **Auth:** Google OAuth + JWT cookies + API keys with scopes
- **Billing:** Stripe Checkout + webhooks
- **Observability:** Prometheus + Grafana + OpenTelemetry

### Key Decisions Made ✅
- [x] Authentication method: **Google OAuth + JWT + API keys**
- [x] Database choice: **PostgreSQL with pgvector**
- [x] Vector database: **pgvector (embedded)** - avoids external dependency
- [x] Hosting platform: **Cloud-agnostic (Docker)** - works on AWS/GCP/Azure
- [x] Pricing model: **Stripe subscriptions** (usage-based quotas enforced)

---

## Timeline Estimate

- **Phase 1:** 1-2 weeks
- **Phase 2:** 2-3 weeks
- **Phase 3:** 1-2 weeks
- **Phase 4:** 2-3 weeks
- **Phase 5:** 3-6 months (ongoing)
- **Phase 6:** 6+ months (future)

**Total to MVP (Phases 1-4):** 6-10 weeks
**Total to Commercial (Phases 1-5):** 4-6 months

---

## Resources

- `docs/notes/COMMERCIAL_VIABILITY_ANALYSIS.md` - Full analysis
- `docs/guides/CRITICAL_FIXES_GUIDE.md` - Code-level security fixes
- `QUICK_REFERENCE.md` - Quick checklist

---

**Last Updated:** 2025-11-23
**Current Phase:** Phase 6 - UI/UX Polish & Production Hardening

