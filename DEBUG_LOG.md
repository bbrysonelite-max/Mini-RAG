# DEBUG LOG - Systematic Verification

## Mission
Debug RAG system returning "I don't have enough information" - trace entire pipeline, verify every step, fix what's broken.

## Diagnostic Results

### STEP 1: Chunk File Verification ✅
- Location: `out/chunks.jsonl`
- Count: **59 chunks**
- Structure: Each has `id`, `content` (36-1200 chars), `source`, `metadata`, `user_id`
- **VERIFIED WORKING**

### STEP 2: BM25 Index & Search ✅  
- Loads 59 chunks from JSONL
- Builds BM25 index successfully
- Search returns 10 results with scores 3.70-6.85
- **VERIFIED WORKING**

### STEP 3: RAG Pipeline End-to-End ✅
- Pipeline initializes with 59 chunks
- Retrieves 5 chunks via BM25
- Chunks have `text` field with 1199-1200 chars
- No abstention (threshold check passes)
- **VERIFIED WORKING**

### STEP 4: Server Context Extraction ✅
- Extracts `chunk_meta.get('text')` successfully
- Generates 3632 chars of context from 3 chunks
- Context is non-empty
- **VERIFIED WORKING**

## Root Cause Identified

### THE DIVERGENCE POINT

Production environment variable:
```python
USE_DB_CHUNKS = os.getenv("USE_DB_CHUNKS", "true")  # DEFAULTS TO TRUE
```

### Two Code Paths

**Local (Working):**
```
USE_DB_CHUNKS=false (implicitly, no env set)
→ load_chunks('out/chunks.jsonl')  
→ CHUNKS = 59 chunks with content
→ ✅ WORKS
```

**Production (Broken):**
```
USE_DB_CHUNKS=true (default)
→ load_chunks_from_db(store)
→ vector_store.fetch_all_chunks()
→ SELECT FROM chunks table
→ CHUNKS = ??? (likely 0 or wrong format)
→ ❌ FAILS
```

### Database Loading Chain

1. `server.py:_reload_chunks_from_db()` calls
2. `chunk_db.py:load_chunks_from_db()` calls  
3. `vector_store.py:fetch_all_chunks()` which runs:
   ```sql
   SELECT id, text, position, start_offset, end_offset, created_at
   FROM chunks
   ORDER BY created_at ASC
   ```
4. Converts to format:
   ```python
   {
     "id": str(row["id"]),
     "content": row["text"],  # ← Maps DB 'text' column to 'content' key
     "source": {"type": "database"},
     "metadata": {...}
   }
   ```

### Why This Breaks

**Hypothesis**: Production database `chunks` table is EMPTY or has 0 rows.

Evidence:
1. Local with JSONL: ✅ Works perfectly
2. Code path logic: ✅ Correct
3. Data format conversion: ✅ Correct  
4. Production behavior: ❌ Returns "no information"
5. Screenshot shows: Retrieved chunks but empty answers

**Conclusion**: Database has no chunks while JSONL has 59 chunks with content.

## Fix Required

### Option A: Quick Fix (Use JSONL in production)
Set Railway environment variable:
```
USE_DB_CHUNKS=false
```

### Option B: Proper Fix (Populate database)
Run on Railway or with Railway DATABASE_URL:
```bash
python scripts/persist_existing_chunks.py
```

This will:
1. Load 59 chunks from `out/chunks.jsonl`
2. Connect to PostgreSQL
3. Insert chunks into `chunks` table
4. Verify persistence

### Option C: Implement Both (Recommended)
1. Populate database with proper data
2. Keep `USE_DB_CHUNKS=false` as fallback
3. Test both paths work

## Next Steps

1. **IMMEDIATE**: Set `USE_DB_CHUNKS=false` in Railway to restore service
2. **SHORT TERM**: Run `persist_existing_chunks.py` to populate database
3. **VERIFICATION**: Test with `USE_DB_CHUNKS=true` after database populated
4. **LONG TERM**: Add health check that verifies chunk count in both JSONL and DB

## Files Modified

None yet - diagnosis only, no code changes made.
