#!/usr/bin/env python3
"""
Remove duplicate chunks from database based on content.
Deduplicates by (document_id, text, position) - keeps the oldest chunk.
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_database

async def dedupe_database():
    """Remove duplicate chunks from database."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5432/rag_brain"
        print(f"Using default DATABASE_URL: {db_url[:50]}...")
    
    print("=" * 60)
    print("Database Chunk Deduplication")
    print("=" * 60)
    
    try:
        db = await init_database(db_url, init_schema=False)
        
        # Count duplicates
        print("\n1. Counting duplicates...")
        duplicate_count = await db.fetch_one(
            """
            SELECT COUNT(*) - COUNT(DISTINCT (document_id, text, position)) as duplicates
            FROM chunks
            """
        )
        dupes = duplicate_count['duplicates'] if duplicate_count else 0
        print(f"   Found {dupes} duplicate chunks")
        
        if dupes == 0:
            print("\n✅ No duplicates found!")
            return True
        
        # Get total count before
        total_before = await db.fetch_one("SELECT COUNT(*) as count FROM chunks")
        count_before = total_before['count'] if total_before else 0
        print(f"\n2. Total chunks before: {count_before}")
        
        # Remove duplicates, keeping the oldest chunk (lowest created_at)
        print("\n3. Removing duplicates (keeping oldest)...")
        result = await db.execute(
            """
            DELETE FROM chunks
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY document_id, text, position 
                               ORDER BY created_at ASC
                           ) as rn
                    FROM chunks
                ) t
                WHERE rn > 1
            )
            """
        )
        
        # Get total count after
        total_after = await db.fetch_one("SELECT COUNT(*) as count FROM chunks")
        count_after = total_after['count'] if total_after else 0
        removed = count_before - count_after
        
        print(f"   ✓ Removed {removed} duplicate chunks")
        print(f"   ✓ Kept {count_after} unique chunks")
        
        print("\n" + "=" * 60)
        print("✅ Deduplication complete!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(dedupe_database())
    sys.exit(0 if success else 1)



