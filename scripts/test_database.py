#!/usr/bin/env python3
"""
Test database connection and schema.
Run this to verify database is properly configured.
"""
import os
import sys
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_database, get_database
from vector_store import VectorStore

async def test_database():
    """Test database connection and basic operations."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    # Get database URL
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("   Set it with: export DATABASE_URL='postgresql://...'")
        return False
    
    print(f"✓ DATABASE_URL is set")
    print(f"  Connection string: {db_url[:50]}...")
    
    try:
        # Initialize database
        print("\n1. Initializing database connection...")
        db = await init_database(db_url, init_schema=False)
        print("   ✓ Database connection established")
        
        # Test basic query
        print("\n2. Testing basic query...")
        result = await db.fetch_one("SELECT version()")
        if result:
            version = result.get("version", "unknown")
            print(f"   ✓ PostgreSQL version: {version[:50]}...")
        
        # Check pgvector extension
        print("\n3. Checking pgvector extension...")
        has_pgvector = await db.check_pgvector()
        if has_pgvector:
            print("   ✓ pgvector extension is installed")
        else:
            print("   ⚠ WARNING: pgvector extension not found")
            print("   Run: CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Check if schema tables exist
        print("\n4. Checking database schema...")
        tables_to_check = [
            "users", "organizations", "workspaces", "projects",
            "sources", "documents", "chunks", "chunk_embeddings"
        ]
        
        missing_tables = []
        for table in tables_to_check:
            result = await db.fetch_one(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                ) as exists
                """,
                (table,)
            )
            if result and result.get("exists"):
                print(f"   ✓ Table '{table}' exists")
            else:
                print(f"   ❌ Table '{table}' is missing")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\n   ⚠ WARNING: {len(missing_tables)} tables are missing")
            print("   Run schema initialization:")
            print("   python scripts/init_railway_db.py")
            print("   OR set init_schema=True in server startup")
        else:
            print("\n   ✓ All required tables exist")
        
        # Test vector store
        print("\n5. Testing vector store...")
        try:
            store = VectorStore(db)
            context = await store.ensure_default_context()
            print("   ✓ Vector store initialized")
            print(f"   ✓ Default context created:")
            print(f"     - Organization ID: {context['organization_id']}")
            print(f"     - Workspace ID: {context['workspace_id']}")
            print(f"     - Project ID: {context['project_id']}")
        except Exception as e:
            print(f"   ❌ Vector store initialization failed: {e}")
            return False
        
        # Check chunk count
        print("\n6. Checking existing chunks...")
        chunks = await store.fetch_all_chunks()
        chunk_count = len(chunks)
        print(f"   ✓ Found {chunk_count} chunks in database")
        
        if chunk_count > 0:
            print(f"   Sample chunk IDs:")
            for i, chunk in enumerate(chunks[:3]):
                chunk_id = chunk.get("id", "unknown")
                text_preview = chunk.get("content", "")[:50]
                print(f"     {i+1}. {chunk_id}: {text_preview}...")
        
        # Health check
        print("\n7. Running health check...")
        health = await db.health_check()
        if health.get("status") == "healthy":
            print("   ✓ Database health check passed")
        else:
            print(f"   ⚠ Health check: {health.get('status', 'unknown')}")
            if health.get("error"):
                print(f"     Error: {health['error']}")
        
        print("\n" + "=" * 60)
        print("✅ Database test completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database())
    sys.exit(0 if success else 1)

