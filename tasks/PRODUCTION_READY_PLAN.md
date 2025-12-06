# Production-Ready Plan - Make Mini-RAG Rock Solid

**Goal:** Transform Mini-RAG from "deployed but broken" to "production-ready, zero broken windows"

**Status:** Starting fresh after 3 days of debugging
**Timeline:** Full day of focused work

---

## Phase 1: Database Foundation (CRITICAL - 30 min)

### ✅ Task 1.1: Fix Schema Syntax Error
- **Status:** ✅ FIXED - Removed trailing comment causing syntax error
- **Commit:** `86a1a78`
- **Next:** Wait for deployment, verify tables created

### Task 1.2: Verify Database Initialization
- [ ] Check Railway logs for "Database schema initialized successfully"
- [ ] Connect to Railway PostgreSQL and verify tables exist:
  ```sql
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public' 
  ORDER BY table_name;
  ```
- [ ] Expected tables: `chunks`, `documents`, `sources`, `workspaces`, `organizations`, `projects`

### Task 1.3: Test Chunk Persistence
- [ ] Upload a test file via UI
- [ ] Verify chunks created in database:
  ```sql
  SELECT COUNT(*) FROM chunks;
  SELECT document_id, COUNT(*) FROM chunks GROUP BY document_id;
  ```
- [ ] Trigger a redeploy
- [ ] Verify chunks still exist after redeploy

**Success Criteria:** Database initialized, chunks persist across redeploys

---

## Phase 2: Error Handling & Robustness (2 hours)

### Task 2.1: Fix Bare Exception Handlers
**Problem:** Code has `except Exception:` that swallows all errors
**Files to fix:**
- `server.py` - Find all bare except clauses
- `raglite.py` - Error handling in ingestion
- `rag_pipeline.py` - LLM call error handling
- `vector_store.py` - Database error handling

**Fix:**
- Replace with specific exceptions
- Add proper logging with context
- Return meaningful error messages to users

### Task 2.2: Add Input Validation
**Problem:** No limits on query length, file size, k parameter
**Fix:**
- Query length: Max 5000 characters
- File size: Max 100MB
- k parameter: Between 1-100
- URL validation: Whitelist patterns for YouTube

**Files:**
- `server.py` - Add Pydantic validators to request models
- `raglite.py` - Add file size checks before processing

### Task 2.3: Fix Race Conditions
**Problem:** Global `INDEX` and `CHUNKS` variables, no locking
**Fix:**
- Add `asyncio.Lock()` for index rebuilds
- Use thread-safe data structures
- Add proper synchronization

**Files:**
- `server.py` - Add locks around INDEX/CHUNKS operations
- `retrieval.py` - Ensure thread-safe access

### Task 2.4: Add Error Recovery
**Problem:** If index rebuild fails, system is broken
**Fix:**
- Keep old index until new one is ready
- Add rollback on failure
- Health check endpoint reports index status

---

## Phase 3: Security Hardening (2 hours)

### Task 3.1: File Upload Security
**Problem:** Path traversal, malicious files, no sanitization
**Fix:**
- Sanitize filenames: Remove `../`, `~`, absolute paths
- Whitelist file extensions: `.pdf`, `.docx`, `.md`, `.txt`, `.vtt`, `.srt`
- Add file size limits (already in 2.2)
- Scan for malicious content (basic checks)

**Files:**
- `server.py` - `ingest_files()` endpoint
- `raglite.py` - File processing functions

### Task 3.2: URL Validation
**Problem:** Command injection risk with `yt-dlp` subprocess
**Fix:**
- Validate YouTube URLs with regex
- Whitelist allowed domains
- Escape shell arguments properly

**Files:**
- `server.py` - `ingest_urls()` endpoint
- `raglite.py` - `ingest_youtube()` function

### Task 3.3: CORS Configuration
**Problem:** No CORS config for production
**Fix:**
- Configure allowed origins
- Set proper headers
- Add preflight handling

**Files:**
- `server.py` - CORS middleware configuration

### Task 3.4: Error Message Sanitization
**Problem:** Error messages expose internal paths
**Fix:**
- Generic messages for users
- Detailed logs server-side only
- Remove file paths from responses

---

## Phase 4: User Experience (1 hour)

### Task 4.1: Better Error Messages
**Problem:** Generic errors confuse users
**Fix:**
- "File upload failed" → "File too large (max 100MB)" or "Unsupported file type"
- "No chunks found" → "No documents uploaded yet. Upload a file to get started."
- "Query failed" → "Unable to process query. Please try again."

**Files:**
- `server.py` - All error responses

### Task 4.2: Upload Progress Feedback
**Problem:** Users don't know if upload is processing
**Fix:**
- Add progress indicator in UI
- Show chunk count after upload
- Display processing status

**Files:**
- `frontend-react/` - Add progress UI
- `server.py` - Return processing status

### Task 4.3: Health Check Improvements
**Problem:** Health check doesn't report useful info
**Fix:**
- Add database status
- Add index status
- Add chunk count
- Add last update time

**Files:**
- `server.py` - `/health` endpoint

---

## Phase 5: Testing & Validation (1 hour)

### Task 5.1: End-to-End Test Suite
- [ ] Upload PDF document
- [ ] Verify chunks created
- [ ] Ask question about document
- [ ] Verify answer with citations
- [ ] Redeploy
- [ ] Verify chunks persist
- [ ] Ask question again (verify persistence)

### Task 5.2: Error Scenario Testing
- [ ] Upload oversized file → Should reject gracefully
- [ ] Upload invalid file type → Should reject gracefully
- [ ] Query with no chunks → Should return helpful message
- [ ] Invalid YouTube URL → Should reject gracefully

### Task 5.3: Performance Testing
- [ ] Upload 10MB PDF → Should complete in <30 seconds
- [ ] Query with 100 chunks → Should return in <2 seconds
- [ ] Concurrent uploads → Should handle gracefully

---

## Phase 6: Documentation & Monitoring (30 min)

### Task 6.1: Update Deployment Docs
- [ ] Document database setup
- [ ] Document environment variables
- [ ] Document known limitations

### Task 6.2: Add Monitoring
- [ ] Verify Prometheus metrics working
- [ ] Check log aggregation
- [ ] Set up alerts for critical errors

---

## Success Criteria

### Must Have (Blocking):
- ✅ Database schema initializes successfully
- ✅ Chunks persist across redeploys
- ✅ No bare exception handlers
- ✅ Input validation on all endpoints
- ✅ File upload security hardened
- ✅ Error messages are user-friendly

### Should Have (High Priority):
- ✅ Race conditions fixed
- ✅ CORS configured
- ✅ Health check reports useful info
- ✅ Upload progress feedback

### Nice to Have (Can defer):
- Advanced monitoring
- Performance optimizations
- Additional test coverage

---

## Execution Order

1. **Wait for schema fix deployment** (5 min)
2. **Verify database works** (10 min)
3. **Fix error handling** (2 hours)
4. **Fix security issues** (2 hours)
5. **Improve UX** (1 hour)
6. **Test everything** (1 hour)
7. **Document** (30 min)

**Total Time:** ~7 hours of focused work

---

## Current Status

- ✅ Schema syntax error fixed
- ⏳ Waiting for deployment
- ⏳ Next: Verify database initialization

Let's make this rock solid! 🚀





