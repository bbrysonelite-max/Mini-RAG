# Mini-RAG – Known Issues & Technical Debt

**Last Updated:** Nov 30, 2025 (post-deployment)

---

## Critical (Blocks Production Use)

### 1. Data Loss on Redeploy
**Problem:** Chunks stored in `out/chunks.jsonl` on container filesystem. Every Railway redeploy wipes all uploaded data.

**Impact:** Users lose all their documents on every deploy.

**Fix Options:**
- **A) Use Postgres for chunks** – Run schema migration, store chunks in DB (survives redeploys)
- **B) Add Railway Volume** – Mount persistent volume to `/app/out/` (quick fix)
- **C) Use S3/blob storage** – Store chunks in cloud storage (scalable, expensive)

**Recommended:** Option B (Railway Volume) for immediate fix, migrate to Option A long-term.

**Effort:** 30 minutes

---

### 2. Anthropic Key Validation Failed
**Problem:** Anthropic API key was set in Railway but returns 401 "invalid x-api-key" on every request.

**Root Cause:** Unknown—possibly truncated during env var sync, or key format issue.

**Workaround:** Deleted `ANTHROPIC_API_KEY` from Railway; app now uses OpenAI only.

**Fix:** 
1. Validate Anthropic key locally before deploying (use `lastmile` when built)
2. Test key in production post-deploy with health check
3. Add fallback to OpenAI if Anthropic fails

**Effort:** 1 hour (after The Last Mile is built)

---

### 3. No Persistent Auth State
**Problem:** With `LOCAL_MODE=true`, anyone with the URL can upload/query. With `LOCAL_MODE=false`, users can't log in (no button/flow visible in UI).

**Impact:** Can't use in production without exposing to public OR can't use with auth enabled.

**Fix:**
1. Add Google OAuth login button to UI when `LOCAL_MODE=false`
2. Implement session persistence (currently sessions lost on redeploy)
3. Add admin role assignment workflow (can't promote users to admin currently)

**Effort:** 4 hours

---

## High Priority (Limits Usefulness)

### 4. No Ingest Status Feedback
**Problem:** Files upload but user doesn't see chunking progress. "0 chunks" message is confusing—looks like failure even when it's still processing.

**Impact:** Users don't know if ingest succeeded until they manually check Sources tab.

**Fix:**
1. Add progress indicator during chunking
2. Show "Processing..." state in UI
3. Add background job queue + webhook to notify when complete

**Effort:** 2 hours (UI) + 4 hours (background jobs)

---

### 5. Missing Database Schema on Fresh Deploys
**Problem:** If Postgres is empty, app starts but features requiring tables (users, api_keys, workspaces) fail silently.

**Impact:** Fresh deployments to new environments break until schema is manually loaded.

**Fix:**
1. Run `db_schema.sql` migration on startup (via Alembic or raw psycopg)
2. Add health check that fails if schema missing
3. Document manual migration step in deployment guide

**Effort:** 2 hours

---

### 6. Env Var Sync Hell
**Problem:** Pushing secrets to Railway requires multiple manual steps, CLI logout/login, and values get truncated/lost.

**Impact:** 48 hours wasted on deployment instead of building features.

**Fix:** Build **The Last Mile** (separate project, in progress).

**Effort:** 2 weeks (Phase 1 MVP)

---

## Medium Priority (Quality of Life)

### 7. No Open-Source LLM Support
**Problem:** Only OpenAI and Anthropic supported. Both are expensive per-token. No free/local inference option.

**Impact:** Running costs scale with usage; can't offer free tier without losing money.

**Fix:**
1. Add Ollama provider (local inference)
2. Add OpenRouter provider (access to 50+ models, some free)
3. Add LM Studio provider
4. Let users select model per request (speed vs quality tradeoff)

**Effort:** 4 hours

---

### 8. Poor Error Messages
**Problem:** Errors like "Not Found" or "401" don't tell user what's actually wrong.

**Impact:** Debugging requires looking at Railway logs (most users won't).

**Fix:**
1. Return descriptive error messages (e.g., "Anthropic API key invalid")
2. Add error boundary in React UI
3. Log errors to Sentry/DataDog for visibility

**Effort:** 2 hours

---

### 9. No Chunk Previews in Sources Tab
**Problem:** Sources tab lists files but clicking them shows "Not Found" if chunks missing.

**Impact:** Can't verify ingestion succeeded without going to Ask tab and querying.

**Fix:**
1. Show chunk count per source
2. Add "View Chunks" modal with preview
3. Add "Re-process" button to retry chunking

**Effort:** 3 hours

---

## Low Priority (Nice to Have)

### 10. No File Type Validation
**Problem:** Users can upload any file; unsupported formats fail silently.

**Impact:** Confusion when .exe or .zip uploads but produces 0 chunks.

**Fix:** Add client-side validation (only allow .pdf, .md, .txt, .docx, .vtt, .srt).

**Effort:** 30 minutes

---

### 11. No Rate Limiting on Ingest
**Problem:** User can spam uploads, rack up OpenAI embedding costs.

**Impact:** Abuse = high bills.

**Fix:** Add rate limit (e.g., 10 files/hour per user).

**Effort:** 1 hour

---

### 12. No Cost Tracking
**Problem:** Don't know how much each request costs (OpenAI tokens).

**Impact:** Can't predict costs or bill customers accurately.

**Fix:** 
1. Log token usage per request
2. Add `/billing/usage` endpoint
3. Show cost estimate in UI

**Effort:** 2 hours

---

## Technical Debt (Refactoring Needed)

### 13. Inconsistent Local vs Production Config
**Problem:** `.env` has `LOCAL_MODE=true`, Railway has `LOCAL_MODE=false` (now true again). Easy to mix up which is which.

**Impact:** Constantly toggling settings, forgetting which env is which.

**Fix:**
1. Separate `.env.local` and `.env.production`
2. Use `lastmile` to manage env-specific secrets
3. Document which settings belong where

**Effort:** 1 hour

---

### 14. No Automated Tests for Deployment
**Problem:** Only unit tests. No integration tests that validate deployment worked (DB connected, LLM reachable, etc.).

**Impact:** Deploy breaks and we don't know until manually testing.

**Fix:**
1. Add post-deploy smoke tests (hit `/health`, `/ask`, `/ingest`)
2. Run in CI/CD pipeline
3. Block deploy if tests fail

**Effort:** 3 hours

---

### 15. No Rollback Strategy
**Problem:** If deploy breaks, only way to fix is deploy again (which takes time + risks more breakage).

**Impact:** Downtime compounds.

**Fix:**
1. Railway supports rollback; document the process
2. Add "Deploy with rollback" workflow (test in staging first)
3. Keep last 3 deployments available for instant rollback

**Effort:** 1 hour (documentation)

---

## Tracking

**Priority:**
- Critical: 3 issues
- High: 3 issues
- Medium: 3 issues
- Low: 3 issues
- Tech Debt: 3 issues

**Estimated Total Effort:** 35 hours

**Recommended Order:**
1. Fix data persistence (Railway Volume) – **30 min**
2. Add open-source LLM support – **4 hours**
3. Fix auth UI (login button + role assignment) – **4 hours**
4. Build The Last Mile MVP – **80 hours** (separate project)
5. Tackle remaining items incrementally

---

## How to Use This Document

1. **Before each session:** Review this list, pick 1-2 items to fix
2. **After fixing:** Move item to `CHANGELOG.md` with date + commit
3. **When adding new issues:** Add to appropriate priority section
4. **Weekly:** Re-prioritize based on user feedback

---

**Built with duct tape and determination. Improving one deploy at a time.**


