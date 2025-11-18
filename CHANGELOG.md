## Changelog

### 2025-11-17
- Added automated test suite `test_phase3_auth.py` covering JWT, chunk user IDs, search filtering, and admin role checks.
- Ran test suite (`venv/bin/python3 test_phase3_auth.py`); 6 tests passed, 1 skipped (needs DATABASE_URL for user service).
- Documented Phase 3 completion in `PHASE3_COMPLETE.md` and ensured honest reporting of test status.

### 2025-11-18
- Verified project dependencies and installed missing database drivers (`psycopg[binary]`, `psycopg-pool`).
- Updated `test_phase3_auth.py` to use an in-memory FakeDatabase so `user_service` tests run without a live PostgreSQL instance.
- Ran full test suite (`cd /Users/brentbryson/Desktop/mini-rag && ./venv/bin/python3 test_phase3_auth.py`); **all 7 tests passed** ✅ (no skips or failures) with FakeDatabase fallback standing in for PostgreSQL.
- Hardened Google OAuth environment loading by pointing `auth.py` directly at the repo `.env`, ensuring CLI utilities launched via stdin also register `oauth.google`.
- Documented remaining manual verification items: capture full browser-based OAuth flow evidence and repeat UserService checks against a live PostgreSQL/pgvector stack when available.


