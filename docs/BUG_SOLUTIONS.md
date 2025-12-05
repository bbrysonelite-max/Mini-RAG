# Bug Solutions and Patterns

This document contains documented bug fixes and patterns that should be checked before fixing any bug. Always reference this file first when encountering issues.

## Purpose

Before fixing any bug:
1. Check this file for similar issues and existing solutions
2. Review the patterns and approaches documented here
3. Apply the appropriate solution or pattern
4. Document new bugs and their fixes here for future reference

## Bug Fix Patterns

### Pattern: File Upload Security
**Issue:** Path traversal, file size limits, file type validation
**Solution:** See `docs/guides/CRITICAL_FIXES_GUIDE.md` section 1 for complete implementation
**Key Points:**
- Always sanitize filenames
- Validate file types against whitelist
- Implement file size limits
- Use UUID-based safe filenames

### Pattern: Input Validation
**Issue:** Missing validation on user inputs
**Solution:** Use Pydantic models for all API endpoints
**Key Points:**
- Validate query length (max 5000 chars)
- Validate `k` parameter (1-100 range)
- Validate URL formats
- Use Field validators for complex checks

### Pattern: Error Handling
**Issue:** Bare except clauses, swallowed errors
**Solution:** Use specific exception types and proper logging
**Key Points:**
- Replace bare `except Exception` with specific exceptions
- Log errors with context
- Return user-friendly error messages
- Don't expose internal paths or stack traces

### Pattern: URL Validation
**Issue:** Unsafe URL handling, command injection risks
**Solution:** Validate URLs before processing
**Key Points:**
- Validate URL format with regex patterns
- Extract IDs safely instead of using full URLs in commands
- Add timeouts to subprocess calls
- Handle subprocess errors gracefully

## Documented Bugs

### Bug: Bare Exception Handlers
**Date:** 2025-11-17
**File(s):** retrieval.py, ingest_common.py, server.py, raglite.py
**Symptoms:** Bare `except:` and `except Exception:` clauses swallow errors silently
**Root Cause:** Generic exception handling without specific types
**Fix:** Replaced with specific exception types:
- JSON parsing: `except json.JSONDecodeError`
- PDF extraction: `except (ValueError, AttributeError, KeyError)`
- YouTube API: `except (NoTranscriptFound, TranscriptsDisabled)`
**Verification:** All exception handlers now catch specific types, logging works properly

### Bug: Missing Custom Exception Classes
**Date:** 2025-11-17
**File(s):** server.py
**Symptoms:** Using HTTPException for all errors, no custom error handling
**Root Cause:** No domain-specific exceptions defined
**Fix:** Created custom exception hierarchy:
- `RAGError` (base)
- `IndexNotFoundError`
- `InvalidQueryError`
- `IngestionError`
Added FastAPI exception handlers for RAGError and general exceptions
**Verification:** Custom exceptions raise appropriate 400/500 status codes with sanitized messages

### Bug: Basic Logging Without Rotation
**Date:** 2025-11-17
**File(s):** server.py
**Symptoms:** Simple logging.basicConfig with no rotation or proper formatting
**Root Cause:** Development-level logging configuration
**Fix:** Implemented production logging:
- RotatingFileHandler (10MB max, 5 backups)
- Separate console handler (WARNING level)
- Structured log format with timestamps
- Logs stored in logs/ directory
**Verification:** Logs rotate properly, formatted output, separate file/console levels

### Bug: No Request Timeouts
**Date:** 2025-11-17
**File(s):** server.py
**Symptoms:** Long-running queries could hang indefinitely
**Root Cause:** Synchronous processing without timeout
**Fix:** Made /ask endpoint async with 30-second timeout:
- Used `asyncio.wait_for` with `asyncio.to_thread`
- Returns 504 on timeout
- Moved processing to `_process_query` helper
**Verification:** Queries timeout after 30 seconds with proper error message

### Bug: Internal Path Exposure
**Date:** 2025-11-17
**File(s):** server.py
**Symptoms:** /api/stats endpoint exposed internal CHUNKS_PATH
**Root Cause:** Debugging convenience left in production code
**Fix:** Removed `"path": CHUNKS_PATH` from stats response
**Verification:** API responses don't expose internal file paths

### Bug: Cannot Create Workspaces
**Date:** 2025-12-04
**File(s):** db_schema.sql, server.py
**Symptoms:** Workspace creation fails with database error
**Root Cause:** Missing database tables - workspace_settings, organizations, workspace_members tables not created
**Fix:** 
1. Run database schema: `psql $DATABASE_URL < db_schema.sql`
2. Or use Alembic: `alembic upgrade head`
3. Verify tables exist: `\dt` in psql
4. Required tables:
   - organizations
   - workspaces
   - workspace_members  
   - workspace_settings
   - user_organizations
**Verification:** 
- POST to `/api/v1/workspaces` with `{"name": "Test"}` should return 200
- GET `/api/v1/workspaces` should list the workspace
- Check browser console for errors

### Bug: RAG Returns "I don't have enough information" for All Queries  
**Date:** 2025-12-04  
**File(s):** server.py, rag_pipeline.py, retrieval.py
**Symptoms:** All questions return "I don't have enough information" even with chunks being retrieved (visible in UI)
**Root Cause:** Two-part issue:
1. Workspace filtering in BM25 search filtered out legacy chunks  
2. Chunk ID mismatch between RAG pipeline and global CHUNKS lookup caused empty context
**Fix:**
1. Modified `_retrieve_bm25()` in rag_pipeline.py to pass `workspace_id=None`
2. Added fallback in server.py `_process_query_with_llm()` to use RAG pipeline chunk data when `_get_chunk_by_id()` returns None
3. Ensures context_text is populated even when chunk IDs don't match
**Verification:**
- Ask any question in the web UI  
- Should return relevant answer with proper context
- Retrieved chunks section should show chunks with content

### Bug Template
When documenting a new bug, use this format:

```markdown
### Bug: [Short Description]
**Date:** YYYY-MM-DD
**File(s):** path/to/file.py
**Symptoms:** What the bug looks like
**Root Cause:** Why it happened
**Fix:** What was changed
**Verification:** How to verify the fix works
```

---

## Notes

- This file should be updated whenever a bug is fixed
- Keep solutions concise but complete
- Reference related files (like docs/guides/CRITICAL_FIXES_GUIDE.md) when appropriate
- Patterns can be reused across similar bugs

