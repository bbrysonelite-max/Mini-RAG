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
**Solution:** See `CRITICAL_FIXES_GUIDE.md` section 1 for complete implementation
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
- Reference related files (like CRITICAL_FIXES_GUIDE.md) when appropriate
- Patterns can be reused across similar bugs

