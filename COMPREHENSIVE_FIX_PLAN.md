# Comprehensive Database Persistence Fix

## Root Causes Identified

### 1. **paste_document Endpoint Breaks Everything** (CRITICAL)
- Clears `CHUNKS = []`
- Calls `ensure_index()` which does nothing in DB mode
- Calls `_persist_chunks_to_db()` which exits because CHUNKS is empty
- **Result:** All chunks lost from memory after every paste

### 2. **Inconsistent Reload Pattern**
- `ingest_files` endpoint: ✓ Correctly reloads from DB
- `paste_document` endpoint: ✗ Does NOT reload from DB
- `ingest_urls` endpoint: ✓ Correctly reloads from DB

### 3. **RAG Pipeline Not Updated After Ingestion**
- Chunks are loaded into `CHUNKS` global array
- But `RAG_PIPELINE.chunks` is NOT updated
- RAG pipeline continues to use old/empty chunks
- **Result:** "No relevant chunks retrieved" error even when data exists

### 4. **_persist_chunks_to_db Logic Is Wrong**
- This function tries to persist from memory → database
- But in DB mode, chunks are ALREADY in database
- It checks `if not CHUNKS: return` and exits
- **Result:** Unnecessary function that causes confusion

---

## The Fix

### Step 1: Create Standardized Reload Function

```python
async def _reload_chunks_from_db() -> int:
    """
    Reload chunks from database into memory and update RAG pipeline.
    
    Returns:
        Number of chunks loaded, or 0 if failed
    """
    global INDEX, CHUNKS, CHUNK_ID_MAP, RAG_PIPELINE
    
    if not USE_DB_CHUNKS:
        return 0
    
    store = _get_vector_store()
    if not store:
        logger.error("Vector store not available for chunk reload")
        return 0
    
    try:
        chunks_from_db = await load_chunks_from_db(store)
        
        async with _get_index_lock():
            CHUNKS = chunks_from_db or []
            CHUNK_ID_MAP = {c.get("id"): c for c in CHUNKS if c.get("id")}
            INDEX = SimpleIndex(CHUNKS)
        
        # CRITICAL: Update RAG pipeline with new chunks
        if RAG_PIPELINE:
            RAG_PIPELINE.set_chunks(CHUNKS)
            logger.info(f"RAG pipeline updated with {len(CHUNKS)} chunks")
        
        logger.info(f"Reloaded {len(CHUNKS)} chunks from database")
        return len(CHUNKS)
    
    except Exception as e:
        logger.error(f"Failed to reload chunks from database: {e}", exc_info=True)
        CHUNKS = []
        INDEX = SimpleIndex([])
        if RAG_PIPELINE:
            RAG_PIPELINE.set_chunks([])
        return 0
```

### Step 2: Fix paste_document Endpoint

**BEFORE** (lines 4074-4082):
```python
chunks_added = result.get("written", 0)

# Rebuild index
global INDEX, CHUNKS
INDEX = None
CHUNKS = []  # ← WIPES ALL CHUNKS!
ensure_index(require=False)  # Does nothing

# Persist to database if available
if chunks_added > 0:
    await _persist_chunks_to_db()  # Exits because CHUNKS is empty
```

**AFTER**:
```python
chunks_added = result.get("written", 0)

# Reload chunks from database (includes newly added chunks)
if chunks_added > 0:
    reloaded_count = await _reload_chunks_from_db()
    logger.info(f"Paste ingestion: added {chunks_added} chunks, total now {reloaded_count}")
```

### Step 3: Verify Other Ingestion Endpoints

**Check `_ingest_files_core` (lines 4472-4502):**
- Already has correct reload logic ✓
- But should use new `_reload_chunks_from_db()` for consistency

**Check `_ingest_urls_core` (lines 2601-2636):**
- Already has correct reload logic ✓
- But should use new `_reload_chunks_from_db()` for consistency

### Step 4: Fix Startup Initialization

Ensure RAG pipeline gets chunks at startup (lines 1242-1278):

```python
if USE_DB_CHUNKS and DB and VECTOR_STORE_AVAILABLE:
    try:
        store = _get_vector_store()
        if store:
            logger.info("Loading chunks from database")
            chunks_from_db = await load_chunks_from_db(store)
            if chunks_from_db:
                async with _get_index_lock():
                    CHUNKS = chunks_from_db
                    CHUNK_ID_MAP = {c.get("id"): c for c in CHUNKS if c.get("id")}
                    INDEX = SimpleIndex(CHUNKS)
                logger.info(f"Loaded {len(CHUNKS)} chunks from database")
            else:
                logger.warning("Database returned 0 chunks - this may indicate:")
                logger.warning("  1. No data has been ingested yet")
                logger.warning("  2. Database was reset/wiped")
                logger.warning("  3. Connection to wrong database")
                CHUNKS = []
                INDEX = SimpleIndex([])
# ... later in startup ...
if MODEL_SERVICE is None:
    MODEL_SERVICE = _init_model_service()

# CRITICAL: Pass loaded chunks to RAG pipeline
RAG_PIPELINE = _init_rag_pipeline(MODEL_SERVICE, chunks=CHUNKS if CHUNKS else None)
logger.info(f"RAG pipeline initialized with {len(CHUNKS)} chunks")
```

### Step 5: Remove/Fix _persist_chunks_to_db

**Option A: Remove it entirely** (recommended)
- In DB mode, chunks are already persisted by `ingest_*_db()` functions
- This function is redundant and causes confusion

**Option B: Make it a no-op in DB mode**
```python
async def _persist_chunks_to_db() -> None:
    """Legacy function for file-based mode only."""
    if USE_DB_CHUNKS:
        logger.debug("_persist_chunks_to_db: skipped (USE_DB_CHUNKS=True, chunks already in DB)")
        return
    
    # ... rest of file-based logic ...
```

### Step 6: Add Verification Endpoint

```python
@app.get("/debug/chunk-status")
async def chunk_status():
    """Debug endpoint to verify chunk state across all systems."""
    db_count = 0
    if DB:
        try:
            count_row = await DB.fetch_one("SELECT COUNT(*) as cnt FROM chunks")
            db_count = count_row["cnt"] if count_row else 0
        except:
            pass
    
    return {
        "USE_DB_CHUNKS": USE_DB_CHUNKS,
        "database_chunks": db_count,
        "memory_chunks": len(CHUNKS),
        "rag_pipeline_chunks": len(RAG_PIPELINE.chunks) if RAG_PIPELINE else 0,
        "index_chunks": len(INDEX.chunks) if INDEX else 0,
        "MODEL_SERVICE_available": MODEL_SERVICE is not None,
        "RAG_PIPELINE_available": RAG_PIPELINE is not None,
        "chunks_match": db_count == len(CHUNKS) == (len(RAG_PIPELINE.chunks) if RAG_PIPELINE else 0),
    }
```

---

## Implementation Order

1. ✅ Create `_reload_chunks_from_db()` function
2. ✅ Fix `paste_document` endpoint  
3. ✅ Update `_ingest_files_core` to use new reload
4. ✅ Update `_ingest_urls_core` to use new reload
5. ✅ Fix startup to pass chunks to RAG pipeline
6. ✅ Add debug endpoint for verification
7. ✅ Test locally
8. ✅ Deploy and verify on Railway

---

## Expected Result After Fix

1. **Ingest file** → Stored to DB → Reloaded to memory → RAG pipeline updated
2. **Query** → RAG pipeline has chunks → Returns relevant results → LLM generates answer
3. **Restart server** → Chunks loaded from DB → RAG pipeline initialized with chunks → Ready to query
4. **Paste document** → Stored to DB → Reloaded to memory → RAG pipeline updated → No data loss

---

## Railway Database Persistence

**To verify Railway database is persistent:**
1. Go to Railway Dashboard
2. Check if there are TWO services:
   - App service (your mini-rag app)
   - PostgreSQL service (separate database)
3. If only ONE service exists, the database is ephemeral (dies with each deploy)

**To add persistent database:**
1. Click "New" → "Database" → "PostgreSQL"
2. Railway will auto-link `DATABASE_URL` to your app
3. Redeploy app to connect to persistent database

