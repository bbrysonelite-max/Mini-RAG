# RAG Pipeline Map - As-Is Architecture

## Verified Working (Local)

### 1. Chunk Storage
- **Location**: `out/chunks.jsonl`
- **Count**: 59 chunks
- **Structure**: Each chunk has `id`, `content`, `source`, `metadata`, `user_id`
- **Status**: ✅ VERIFIED - All chunks have content (36-1200 chars)

### 2. BM25 Retrieval
- **Implementation**: `retrieval.py` - `SimpleIndex` class
- **Input**: Query string + k (number of results)
- **Process**:
  1. Loads chunks from JSONL
  2. Builds BM25 index on `content` field
  3. Returns list of `(chunk_index, score)` tuples
- **Output**: Array of chunk indices + BM25 scores
- **Status**: ✅ VERIFIED - Returns 10 results with scores 3.70-6.85

### 3. RAG Pipeline
- **Implementation**: `rag_pipeline.py` - `RAGPipeline` class
- **Process**:
  1. Calls BM25 search → gets chunk indices
  2. Converts indices to `Chunk` TypedDict with `text` field
  3. Wraps in `ChunkWithScore` format
  4. Checks abstention threshold (0.1)
  5. Returns `RetrieveResult`
- **Output Structure**:
  ```python
  {
    'chunks': [
      {
        'chunk': {'id': '...', 'text': '...', 'position': 0, ...},
        'score': 6.85,
        'source': 'bm25'
      }
    ],
    'abstained': False,
    'metadata': {...}
  }
  ```
- **Status**: ✅ VERIFIED - Returns chunks with `text` field populated

### 4. Server Context Extraction
- **Implementation**: `server.py` - `_process_query_with_llm()`
- **Process**:
  ```python
  for entry in chunk_entries:
      chunk_meta = entry.get('chunk', {})
      content = chunk_meta.get('text', '') or chunk_meta.get('content', '')
      context_sections.append(f"Source {idx}:\n{content}")
  ```
- **Status**: ✅ VERIFIED - Extracts 3632 chars of context locally

### 5. LLM Prompt
- **Prompt Template**:
  ```
  Answer using the context below. Be helpful and synthesize.
  Cite sources. If unrelated, explain what's missing.
  
  Context: [3632 chars]
  Question: [user query]
  ```
- **Status**: ✅ VERIFIED - Prompt assembled correctly locally

## Production Divergence Point

### Critical Environment Variable
```python
USE_DB_CHUNKS = os.getenv("USE_DB_CHUNKS", "true")  # DEFAULTS TO TRUE
```

### Two Code Paths

**Path A: USE_DB_CHUNKS=false (File-based - VERIFIED WORKING)**
```
startup_event() → 
  ensure_index() → 
    load_chunks('out/chunks.jsonl') →
      CHUNKS = [59 chunks with content]
```

**Path B: USE_DB_CHUNKS=true (Database - PRODUCTION DEFAULT - UNTESTED)**
```
startup_event() →
  _reload_chunks_from_db() →
    store.fetch_all_chunks() →
      CHUNKS = [??? from PostgreSQL]
```

## Root Cause Hypothesis

**PRODUCTION USES DATABASE PATH BUT DATABASE IS EMPTY**

Evidence:
1. Local tests with JSONL file: ✅ WORKS
2. Production screenshot shows: Chunk retrieved but LLM says "no information"
3. Default setting: `USE_DB_CHUNKS=true`
4. Database chunks never verified/tested

## Verification Needed

1. **Check Railway DATABASE_URL** - Is it set?
2. **Query production database** - How many chunks in `chunks` table?
3. **Verify chunk structure in DB** - Do they have `content` or `text` field?

## Fix Options

### Option A: Use JSONL in production (Fast)
Set in Railway: `USE_DB_CHUNKS=false`

### Option B: Persist JSONL to database (Proper)
Run: `python scripts/persist_existing_chunks.py` with Railway DATABASE_URL

### Option C: Hybrid (Belt & Suspenders)
1. Persist to database
2. Set `USE_DB_CHUNKS=false` as fallback
3. Test both paths

