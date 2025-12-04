# Database Persistence Bugs - Root Cause Analysis

## Bug #1: paste_document Endpoint Wipes CHUNKS Array

**Location:** `server.py` lines 4075-4078

```python
# Rebuild index
global INDEX, CHUNKS
INDEX = None
CHUNKS = []  # <-- CRITICAL: Empties all chunks!
ensure_index(require=False)  # Does NOTHING in DB mode (returns early)
```

**Impact:** When `USE_DB_CHUNKS=True`, `ensure_index()` returns immediately without reloading (line 1406-1416), leaving `CHUNKS = []`. The subsequent call to `_persist_chunks_to_db()` checks `if not CHUNKS: return` (line 319), so it persists **nothing**.

**Result:** Every paste operation wipes all chunks from memory and fails to persist.

---

## Bug #2: _persist_chunks_to_db Has Backwards Logic

**Location:** `server.py` lines 313-334

```python
async def _persist_chunks_to_db() -> None:
    store = _get_vector_store()
    if not store:
        return
    try:
        ensure_index(require=False)  # Does nothing in DB mode
        if not CHUNKS:  # Checks in-memory chunks
            return  # Exits if empty!
        # ... persist logic
```

**Problem:** This function tries to persist from **memory → database**, but in DB mode chunks are ALREADY in the database (stored by `ingest_docs_db()`). The function should not be called at all.

**Current wrong flow:**
1. Ingest → Store to DB ✓
2. Clear CHUNKS = [] ✗
3. Call _persist_chunks_to_db() which sees empty CHUNKS and returns ✗

**Correct flow should be:**
1. Ingest → Store to DB ✓
2. Reload CHUNKS from DB ✓
3. Update INDEX and RAG_PIPELINE ✓

---

## Bug #3: Inconsistent Reload After Ingestion

**Files endpoint** (`_ingest_files_core`, lines 4472-4502): ✓ Correctly reloads
```python
if total > 0:
    INDEX = None
    CHUNKS = []
    if USE_DB_CHUNKS:
        chunks_from_db = await load_chunks_from_db(store)
        if chunks_from_db:
            CHUNKS = chunks_from_db  # Reloads!
```

**Paste endpoint** (lines 4075-4082): ✗ Does NOT reload
```python
INDEX = None
CHUNKS = []
ensure_index(require=False)  # Returns early, doesn't reload
await _persist_chunks_to_db()  # Fails because CHUNKS is empty
```

---

## Bug #4: Startup Load May Fail Silently

**Location:** `server.py` lines 1242-1258

```python
if USE_DB_CHUNKS and DB and VECTOR_STORE_AVAILABLE:
    try:
        chunks_from_db = await load_chunks_from_db(store)
        if chunks_from_db:
            CHUNKS = chunks_from_db
            logger.info(f"Loaded {len(CHUNKS)} chunks from database")
        else:
            logger.info("No chunks in database yet")  # Logs as INFO, not ERROR
```

If `load_chunks_from_db()` returns empty list, it's logged as "No chunks in database yet" - but user may have ingested data!

---

## Fix Strategy

1. **Fix paste_document endpoint** to reload chunks from DB after ingestion
2. **Remove or fix _persist_chunks_to_db()** - it shouldn't be needed in DB mode
3. **Standardize reload pattern** across all ingestion endpoints
4. **Add verification** - after reload, check CHUNKS count matches DB count
5. **Improve logging** - distinguish between "no data" vs "failed to load data"

