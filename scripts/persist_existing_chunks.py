#!/usr/bin/env python3
"""
Persist existing chunks from files to PostgreSQL database.
Run this to migrate chunks from file storage to database storage.
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_database
from vector_store import VectorStore
from raglite import load_chunks

async def persist_chunks():
    """Load chunks from file and persist to database."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5432/rag_brain"
        print(f"Using default DATABASE_URL: {db_url[:50]}...")
    
    chunks_path = os.environ.get("CHUNKS_PATH", "out/chunks.jsonl")
    
    print("=" * 60)
    print("Persist Existing Chunks to Database")
    print("=" * 60)
    print(f"\nChunks file: {chunks_path}")
    
    if not os.path.exists(chunks_path):
        print(f"\n❌ Chunks file not found: {chunks_path}")
        return False
    
    # Load chunks from file
    print("\n1. Loading chunks from file...")
    try:
        chunks = load_chunks(chunks_path)
        print(f"   ✓ Loaded {len(chunks)} chunks from file")
    except Exception as e:
        print(f"   ❌ Failed to load chunks: {e}")
        return False
    
    if not chunks:
        print("\n⚠ No chunks to persist")
        return True
    
    # Initialize database and vector store
    print("\n2. Connecting to database...")
    try:
        db = await init_database(db_url, init_schema=False)
        store = VectorStore(db)
        print("   ✓ Database connected")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    
    # Ensure default context
    print("\n3. Ensuring default context...")
    try:
        context = await store.ensure_default_context()
        print("   ✓ Default context ready")
    except Exception as e:
        print(f"   ❌ Failed to create context: {e}")
        return False
    
    # Persist chunks
    print("\n4. Persisting chunks to database...")
    import uuid
    entries = []
    for idx, chunk in enumerate(chunks):
        chunk_id = chunk.get("id")
        if not chunk_id:
            # Generate UUID if missing
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk.get('content', '')[:100]}{idx}"))
        entries.append((chunk_id, chunk))
    
    try:
        await store.ensure_chunks(entries, context)
        print(f"   ✓ Persisted {len(entries)} chunks to database")
    except Exception as e:
        print(f"   ❌ Failed to persist chunks: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify persistence
    print("\n5. Verifying persistence...")
    try:
        db_chunks = await store.fetch_all_chunks()
        print(f"   ✓ Found {len(db_chunks)} chunks in database")
        
        if len(db_chunks) >= len(chunks):
            print("\n" + "=" * 60)
            print("✅ Success! Chunks persisted to database")
            print("=" * 60)
            return True
        else:
            print(f"\n⚠ Warning: Expected {len(chunks)} chunks, found {len(db_chunks)}")
            return False
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(persist_chunks())
    sys.exit(0 if success else 1)




