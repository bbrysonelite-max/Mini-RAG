#!/usr/bin/env python3
"""
Diagnostic script to trace RAG retrieval path.
Following Expert Guidance: "Fix chunking and PROVE retrieval is actually working"
"""
import json
import os
import sys

# Step 1: Verify chunks file exists and has content
print("=" * 60)
print("STEP 1: Verify Chunk Storage")
print("=" * 60)

chunks_path = "out/chunks.jsonl"
if os.path.exists(chunks_path):
    with open(chunks_path, 'r') as f:
        lines = f.readlines()
    print(f"✓ Chunks file exists: {chunks_path}")
    print(f"✓ Total lines: {len(lines)}")
    
    if lines:
        first_chunk = json.loads(lines[0])
        print(f"\n✓ First chunk keys: {list(first_chunk.keys())}")
        print(f"✓ First chunk ID: {first_chunk.get('id', 'NO ID')}")
        content = first_chunk.get('content', first_chunk.get('text', 'NO CONTENT'))
        print(f"✓ First chunk content (first 100 chars): {content[:100]}...")
        print(f"✓ Content length: {len(content)} chars")
else:
    print(f"✗ Chunks file NOT FOUND: {chunks_path}")
    sys.exit(1)

# Step 2: Test BM25 retrieval
print("\n" + "=" * 60)
print("STEP 2: Test BM25 Retrieval (SimpleIndex)")
print("=" * 60)

try:
    from retrieval import SimpleIndex, load_chunks
    
    chunks = load_chunks(chunks_path)
    print(f"✓ Loaded {len(chunks)} chunks from JSONL")
    
    index = SimpleIndex(chunks)
    print(f"✓ BM25 index built")
    
    # Test query
    test_query = "AI business strategy"
    results = index.search(test_query, k=5)
    print(f"\n✓ Query: '{test_query}'")
    print(f"✓ Results returned: {len(results)}")
    
    for idx, (i, score) in enumerate(results[:3]):
        chunk = chunks[i]
        content = chunk.get('content', chunk.get('text', 'NO CONTENT'))
        print(f"\n  Result {idx+1}:")
        print(f"    Score: {score:.4f}")
        print(f"    Chunk ID: {chunk.get('id', 'NO ID')}")
        print(f"    Content preview: {content[:100]}...")
except Exception as e:
    print(f"✗ BM25 retrieval failed: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Test RAG Pipeline
print("\n" + "=" * 60)
print("STEP 3: Test RAG Pipeline")
print("=" * 60)

try:
    import asyncio
    from rag_pipeline import RAGPipeline
    
    # Initialize pipeline with chunks
    pipeline = RAGPipeline(chunks_path=chunks_path)
    print(f"✓ RAG Pipeline initialized")
    print(f"✓ Pipeline has {len(pipeline.chunks)} chunks")
    print(f"✓ Pipeline has BM25 index: {pipeline.bm25_index is not None}")
    
    async def test_retrieve():
        opts = {
            'projectId': 'default',
            'userQuery': test_query,
            'topK_bm25': 10,
            'maxChunksForContext': 5,
        }
        result = await pipeline.retrieve(opts)
        return result
    
    result = asyncio.run(test_retrieve())
    chunk_entries = result.get('chunks', [])
    metadata = result.get('metadata', {})
    
    print(f"\n✓ Retrieval result:")
    print(f"    BM25 results: {metadata.get('bm25_results', 0)}")
    print(f"    Vector results: {metadata.get('vector_results', 0)}")
    print(f"    Final chunks: {len(chunk_entries)}")
    print(f"    Abstained: {result.get('abstained', False)}")
    
    if chunk_entries:
        print(f"\n✓ First returned chunk structure:")
        entry = chunk_entries[0]
        print(f"    Entry keys: {list(entry.keys())}")
        print(f"    Entry type: {type(entry)}")
        
        chunk = entry.get('chunk', {})
        print(f"    Chunk keys: {list(chunk.keys())}")
        print(f"    Chunk type: {type(chunk)}")
        
        # Try all possible content locations
        text = chunk.get('text', '')
        content = chunk.get('content', '')
        entry_text = entry.get('text', '')
        entry_content = entry.get('content', '')
        
        print(f"\n    chunk.text: '{text[:50]}...' (len={len(text)})")
        print(f"    chunk.content: '{content[:50]}...' (len={len(content)})")
        print(f"    entry.text: '{entry_text[:50] if entry_text else 'EMPTY'}' (len={len(entry_text)})")
        print(f"    entry.content: '{entry_content[:50] if entry_content else 'EMPTY'}' (len={len(entry_content)})")
        
        if text:
            print(f"\n✓ SUCCESS: Chunk has 'text' field with content!")
        elif content:
            print(f"\n⚠ WARNING: Chunk has 'content' but not 'text' - mismatch!")
        else:
            print(f"\n✗ FAILURE: No text content found in chunk!")
    else:
        print(f"\n✗ FAILURE: No chunks returned from retrieval!")

except Exception as e:
    print(f"✗ RAG Pipeline test failed: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Simulate server.py extraction logic
print("\n" + "=" * 60)
print("STEP 4: Simulate server.py Content Extraction")
print("=" * 60)

try:
    if 'chunk_entries' in dir() and chunk_entries:
        for idx, entry in enumerate(chunk_entries[:3]):
            chunk_meta = entry.get("chunk", {}) or {}
            
            # This is exactly what server.py does
            content = (
                chunk_meta.get("text", "") or 
                chunk_meta.get("content", "") or
                entry.get("text", "") or
                entry.get("content", "") or
                ""
            ).strip()
            
            print(f"\n  Entry {idx}:")
            print(f"    Extracted content length: {len(content)}")
            print(f"    Content preview: {content[:100]}..." if content else "    ✗ NO CONTENT EXTRACTED!")
            
        if all((entry.get("chunk", {}) or {}).get("text") for entry in chunk_entries[:3]):
            print(f"\n✓ SUCCESS: Content extraction works correctly!")
        else:
            print(f"\n✗ FAILURE: Content extraction is broken!")
except Exception as e:
    print(f"✗ Simulation failed: {e}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)

