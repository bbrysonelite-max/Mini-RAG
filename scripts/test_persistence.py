#!/usr/bin/env python3
"""
Test chunk persistence across redeploys.

This script:
1. Checks current chunk count in database
2. Provides instructions for uploading files
3. Verifies chunks are stored in database
4. Guides through Railway deployment test
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_database
from vector_store import VectorStore

async def check_chunks():
    """Check current chunk count in database."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Try localhost for Docker Compose
        db_url = "postgresql://postgres:postgres@localhost:5432/rag_brain"
        print(f"⚠ DATABASE_URL not set, using: {db_url[:50]}...")
    
    try:
        db = await init_database(db_url, init_schema=False)
        store = VectorStore(db)
        
        chunks = await store.fetch_all_chunks()
        chunk_count = len(chunks)
        
        print("=" * 60)
        print("Chunk Persistence Test")
        print("=" * 60)
        print(f"\n📊 Current chunk count in database: {chunk_count}")
        
        if chunk_count > 0:
            print(f"\n✅ Found {chunk_count} chunks in database!")
            print("\nSample chunks:")
            for i, chunk in enumerate(chunks[:3]):
                chunk_id = chunk.get("id", "unknown")
                text_preview = chunk.get("content", "")[:60]
                print(f"  {i+1}. {chunk_id}: {text_preview}...")
        else:
            print("\n⚠ No chunks found in database yet.")
            print("\nTo add chunks:")
            print("  1. Start your server: uvicorn server:app --reload")
            print("  2. Upload files via:")
            print("     - Web UI: http://localhost:8000/app")
            print("     - API: POST /api/ingest/files")
            print("  3. Run this script again to verify chunks")
        
        print("\n" + "=" * 60)
        print("Next Steps for Railway Test:")
        print("=" * 60)
        print("\n1. ✅ Upload test documents (create chunks)")
        print("2. ✅ Verify chunks in database (this script)")
        print("3. ⏳ Deploy to Railway:")
        print("   git add .")
        print("   git commit -m 'Test persistence'")
        print("   git push")
        print("4. ⏳ After Railway redeploys, check Railway database:")
        print("   - Use Railway DATABASE_URL")
        print("   - Run: DATABASE_URL='railway_url' python3 scripts/test_persistence.py")
        print("\nExpected: Chunks should persist because they're in PostgreSQL!")
        
        return chunk_count
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return -1

if __name__ == "__main__":
    count = asyncio.run(check_chunks())
    sys.exit(0 if count >= 0 else 1)





