# Database Fixes Summary

## Issues Fixed

### 1. Placeholder Format Mismatch ✅
**Problem**: `vector_store.py` used PostgreSQL native placeholders (`$1, $2, ...`) while `database.py` converts them to psycopg format (`%s`). This inconsistency could cause query failures.

**Fix**: Updated `ensure_chunks()` method to use `%s` placeholders directly, matching the format expected by the database layer.

### 2. UUID Validation ✅
**Problem**: Chunk IDs were passed as strings without validation, which could cause PostgreSQL errors if invalid UUIDs were provided.

**Fix**: Added UUID validation before insertion:
- Validates UUID format using Python's `uuid.UUID()`
- Skips invalid chunk IDs with a warning
- Ensures all inserted chunks have valid UUIDs

### 3. Error Handling ✅
**Problem**: Database errors were silently swallowed with `continue`, making it impossible to diagnose persistence failures.

**Fix**: Improved error handling:
- Logs all errors with full stack traces
- Tracks success/failure counts
- Raises exception if ALL chunks fail (prevents silent failures)
- Provides clear logging for debugging

### 4. Database Diagnostic Script ✅
**Created**: `scripts/test_database.py` - A comprehensive test script that:
- Verifies database connection
- Checks pgvector extension
- Validates schema tables exist
- Tests vector store initialization
- Reports chunk counts
- Performs health checks

## How to Use

### Test Database Connection
```bash
# Set your database URL
export DATABASE_URL="postgresql://user:password@host:port/database"

# Run the test script
python scripts/test_database.py
```

### Verify Schema Initialization
The database schema is automatically initialized on server startup if `init_schema=True` is set (which it is by default in `server.py`).

To manually initialize:
```bash
python scripts/init_railway_db.py
```

### Check Chunk Persistence
After uploading files, chunks are automatically persisted to the database. To verify:
1. Upload a file via `/api/ingest/files`
2. Check logs for "Successfully persisted X chunks to database"
3. Run the test script to see chunk count

## Key Changes Made

### `vector_store.py`
- **`ensure_chunks()` method**:
  - Changed placeholders from `$1, $2, ...` to `%s`
  - Added UUID validation
  - Improved error handling and logging
  - Added success/failure tracking
  - Updated `ON CONFLICT` clause to update all fields

## Database Schema

The database uses PostgreSQL with pgvector extension. Key tables:
- `chunks` - Stores document chunks with text and metadata
- `chunk_embeddings` - Stores vector embeddings for semantic search
- `organizations`, `workspaces`, `projects` - Multi-tenant structure
- `sources`, `documents` - Document tracking

## Troubleshooting

### "Table does not exist" errors
Run schema initialization:
```bash
python scripts/init_railway_db.py
```

### "pgvector extension not found"
Connect to your database and run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Chunks not persisting
1. Check server logs for errors
2. Verify `DATABASE_URL` is set correctly
3. Run `scripts/test_database.py` to diagnose
4. Check that `VECTOR_STORE_AVAILABLE` is `True` in server logs

### UUID format errors
The fix validates UUIDs before insertion. If you see warnings about invalid UUIDs, check the chunk ID generation in `server.py` (`_normalize_chunk_uuid` function).

## Next Steps

1. ✅ Database fixes complete
2. ⏳ Test database connection in production
3. ⏳ Verify chunks persist across redeploys
4. ⏳ Test chunk retrieval on startup



