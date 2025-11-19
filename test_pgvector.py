"""
Test script for pgvector integration.

Tests:
1. Database connection and schema initialization
2. Vector storage operations (insert, search, delete)
3. RAG Pipeline with pgvector
4. Performance comparison: pgvector vs in-memory

Prerequisites:
- PostgreSQL with pgvector extension installed
- DATABASE_URL environment variable set

Run with: python test_pgvector.py
"""

import asyncio
import os
import sys
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test 1: Database connection and pgvector availability."""
    print("\n" + "="*60)
    print("TEST 1: Database Connection & pgvector")
    print("="*60)
    
    try:
        from database import init_database
        
        # Check if DATABASE_URL is set
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("✗ DATABASE_URL not set")
            print("  Set it like: export DATABASE_URL='postgresql://user:pass@localhost/dbname'")
            return False
        
        print(f"✓ DATABASE_URL configured")
        
        # Initialize database
        db = await init_database(init_schema=False)
        print("✓ Database connection established")
        
        # Check pgvector
        has_pgvector = await db.check_pgvector()
        if has_pgvector:
            print("✓ pgvector extension available")
        else:
            print("✗ pgvector extension not found")
            print("  Install with: CREATE EXTENSION vector;")
            return False
        
        # Health check
        health = await db.health_check()
        print(f"✓ Health check: {health['status']}")
        
        return True
    
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  Install psycopg: pip install 'psycopg[binary]' psycopg-pool")
        return False
    
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


async def test_vector_store_operations():
    """Test 2: Vector store CRUD operations."""
    print("\n" + "="*60)
    print("TEST 2: Vector Store Operations")
    print("="*60)
    
    try:
        from vector_store import VectorStore
        from database import init_database
        
        db = await init_database()
        vector_store = VectorStore(db)

        # Ensure prerequisite records exist for chunk foreign keys
        owner = await db.fetch_one("SELECT id FROM users LIMIT 1")
        new_owner = False
        if not owner:
            owner = await db.fetch_one(
                """
                INSERT INTO users (email, name, role)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                ("vector-owner@example.com", "Vector Owner", "admin"),
            )
            new_owner = True
        owner_id = owner["id"]

        org = await db.fetch_one(
            """
            INSERT INTO organizations (name, slug)
            VALUES ($1, $2)
            RETURNING id
            """,
            ("Vector Org", f"vector-org-{uuid.uuid4().hex[:6]}")
        )
        org_id = org["id"]

        workspace = await db.fetch_one(
            """
            INSERT INTO workspaces (organization_id, name, slug)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            (org_id, "Vector Workspace", f"vector-ws-{uuid.uuid4().hex[:6]}")
        )
        workspace_id = workspace["id"]

        project = await db.fetch_one(
            """
            INSERT INTO projects (organization_id, workspace_id, owner_id, name, description, namespace, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            (
                org_id,
                workspace_id,
                owner_id,
                "Vector Project",
                "Test project for vector store ops",
                f"vector-proj-{uuid.uuid4().hex[:8]}",
                "ready",
            ),
        )
        project_id = project["id"]

        source = await db.fetch_one(
            """
            INSERT INTO sources (project_id, workspace_id, type, uri, status)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            (project_id, workspace_id, "document", "vector://test", "ready"),
        )
        source_id = source["id"]

        document = await db.fetch_one(
            """
            INSERT INTO documents (source_id, workspace_id, title, language)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            (source_id, workspace_id, "Vector Doc", "en"),
        )
        document_id = document["id"]

        test_chunk_id = str(uuid.uuid4())
        test_embedding = [0.1] * 1536  # Dummy 1536-dim vector
        test_model = "text-embedding-3-small"
        chunk_text = "Vector store test chunk"

        async def insert_chunk(chunk_id: str, text: str, position: int = 0) -> None:
            await db.execute(
                """
                INSERT INTO chunks (id, organization_id, workspace_id, document_id, project_id, text, position)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                (chunk_id, org_id, workspace_id, document_id, project_id, text, position),
            )

        await insert_chunk(test_chunk_id, chunk_text, 0)
        
        # Test insert
        print("\nTesting insert...")
        success = await vector_store.insert_embedding(
            chunk_id=test_chunk_id,
            embedding=test_embedding,
            model_id=test_model
        )
        if success:
            print("✓ Single embedding inserted")
        else:
            print("✗ Insert failed")
            return False
        
        # Test retrieve
        print("\nTesting retrieve...")
        result = await vector_store.get_embedding(test_chunk_id)
        if result and result['chunk_id'] == test_chunk_id:
            print(f"✓ Embedding retrieved (model={result['model_id']})")
        else:
            print("✗ Retrieve failed")
            return False
        
        # Test batch insert
        print("\nTesting batch insert...")
        batch_embeddings = []
        for i in range(2, 11):
            cid = str(uuid.uuid4())
            await insert_chunk(cid, f"Vector chunk {i}", i)
            batch_embeddings.append((cid, [0.1 * i] * 1536, test_model))
        batch_result = await vector_store.insert_embeddings_batch(batch_embeddings)
        if batch_result['inserted'] == 9:
            print(f"✓ Batch inserted {batch_result['inserted']} embeddings")
        else:
            print(f"✗ Batch insert issues: {batch_result}")
        
        # Test count
        count = await vector_store.count_embeddings()
        print(f"✓ Total embeddings in store: {count}")
        
        # Test delete
        print("\nTesting delete...")
        deleted = await vector_store.delete_embedding(test_chunk_id)
        if deleted:
            print("✓ Embedding deleted")
        else:
            print("✗ Delete failed")
        
        # Clean up test data
        for chunk_id, *_ in batch_embeddings:
            await vector_store.delete_embedding(chunk_id)

        # Cleanup inserted records
        await db.execute("DELETE FROM chunks WHERE document_id = $1", (document_id,))
        await db.execute("DELETE FROM documents WHERE id = $1", (document_id,))
        await db.execute("DELETE FROM sources WHERE id = $1", (source_id,))
        await db.execute("DELETE FROM projects WHERE id = $1", (project_id,))
        await db.execute("DELETE FROM workspaces WHERE id = $1", (workspace_id,))
        await db.execute("DELETE FROM organizations WHERE id = $1", (org_id,))
        if new_owner:
            await db.execute("DELETE FROM users WHERE id = $1", (owner_id,))
 
        return True
    
    except Exception as e:
        print(f"✗ Vector store operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rag_pipeline_with_pgvector():
    """Test 3: RAG Pipeline with pgvector."""
    print("\n" + "="*60)
    print("TEST 3: RAG Pipeline with pgvector")
    print("="*60)
    
    chunks_path = "out/chunks.jsonl"
    
    if not os.path.exists(chunks_path):
        print(f"✗ Chunks file not found: {chunks_path}")
        print("  Run ingestion first")
        return False
    
    if not os.getenv("OPENAI_API_KEY"):
        print("✗ OPENAI_API_KEY not set - skipping pgvector test")
        return False
    
    try:
        from rag_pipeline import RAGPipeline
        from model_service_impl import ConcreteModelService
        from vector_store import VectorStore
        from database import init_database
        
        # Initialize
        db = await init_database()
        model_service = ConcreteModelService()
        vector_store = VectorStore(db)
        
        pipeline = RAGPipeline(
            chunks_path=chunks_path,
            model_service=model_service,
            vector_store=vector_store,
            use_pgvector=True
        )
        
        print(f"✓ Pipeline initialized with {len(pipeline.chunks)} chunks")
        print(f"  Using pgvector: {pipeline.use_pgvector}")
        
        # Build vector index (limit for testing)
        print("\nBuilding vector index (first 50 chunks for testing)...")
        
        # Temporarily limit chunks for faster testing
        original_chunks = pipeline.chunks
        pipeline.chunks = pipeline.chunks[:50]
        
        stats = await pipeline.build_vector_index(batch_size=10)
        
        if 'error' in stats:
            print(f"✗ Failed to build index: {stats['error']}")
            return False
        
        print(f"✓ Index built:")
        print(f"  Embedded: {stats['chunks_embedded']}")
        print(f"  Storage: {stats['storage_type']}")
        
        # Test hybrid retrieval
        query = "what is the main topic"
        print(f"\nTesting hybrid retrieval: '{query}'")
        
        result = await pipeline.retrieve({
            'projectId': 'default',
            'userQuery': query,
            'topK_bm25': 10,
            'topK_vector': 10
        })
        
        chunks = result.get('chunks', [])
        print(f"✓ Retrieved {len(chunks)} chunks")
        
        if chunks:
            print(f"\nTop result:")
            print(f"  Source: {chunks[0]['source']}")
            print(f"  Score: {chunks[0]['score']:.3f}")
            print(f"  Preview: {chunks[0]['chunk']['text'][:80]}...")
        
        metadata = result.get('metadata', {})
        print(f"\nMetadata:")
        print(f"  BM25 results: {metadata.get('bm25_results', 0)}")
        print(f"  Vector results: {metadata.get('vector_results', 0)}")
        print(f"  Final: {metadata.get('final_count', 0)}")
        
        # Restore chunks
        pipeline.chunks = original_chunks
        
        return True
    
    except Exception as e:
        print(f"✗ RAG Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_comparison():
    """Test 4: Performance comparison pgvector vs in-memory."""
    print("\n" + "="*60)
    print("TEST 4: Performance Comparison")
    print("="*60)
    
    chunks_path = "out/chunks.jsonl"
    
    if not os.path.exists(chunks_path) or not os.getenv("OPENAI_API_KEY"):
        print("✗ Skipping performance test (missing chunks or API key)")
        return False
    
    try:
        import time
        from rag_pipeline import RAGPipeline
        from model_service_impl import ConcreteModelService
        from vector_store import VectorStore
        from database import init_database
        
        model_service = ConcreteModelService()
        
        # Test in-memory
        print("\nTesting in-memory vector search...")
        pipeline_memory = RAGPipeline(
            chunks_path=chunks_path,
            model_service=model_service,
            use_pgvector=False
        )
        
        # Limit to 100 chunks for comparison
        pipeline_memory.chunks = pipeline_memory.chunks[:100]
        
        start = time.time()
        await pipeline_memory.build_vector_index(batch_size=20)
        memory_build_time = time.time() - start
        
        start = time.time()
        result_memory = await pipeline_memory.retrieve({
            'projectId': 'default',
            'userQuery': 'test query',
            'topK_bm25': 10,
            'topK_vector': 10
        })
        memory_query_time = time.time() - start
        
        print(f"✓ In-memory:")
        print(f"  Build time: {memory_build_time:.2f}s")
        print(f"  Query time: {memory_query_time:.3f}s")
        print(f"  Results: {len(result_memory['chunks'])}")
        
        # Test pgvector
        print("\nTesting pgvector search...")
        db = await init_database()
        vector_store = VectorStore(db)
        
        pipeline_pg = RAGPipeline(
            chunks_path=chunks_path,
            model_service=model_service,
            vector_store=vector_store,
            use_pgvector=True
        )
        
        pipeline_pg.chunks = pipeline_pg.chunks[:100]
        
        start = time.time()
        await pipeline_pg.build_vector_index(batch_size=20)
        pg_build_time = time.time() - start
        
        start = time.time()
        result_pg = await pipeline_pg.retrieve({
            'projectId': 'default',
            'userQuery': 'test query',
            'topK_bm25': 10,
            'topK_vector': 10
        })
        pg_query_time = time.time() - start
        
        print(f"✓ pgvector:")
        print(f"  Build time: {pg_build_time:.2f}s")
        print(f"  Query time: {pg_query_time:.3f}s")
        print(f"  Results: {len(result_pg['chunks'])}")
        
        print(f"\nComparison:")
        print(f"  pgvector is {memory_query_time/pg_query_time:.1f}x {'faster' if pg_query_time < memory_query_time else 'slower'} for queries")
        
        return True
    
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("="*60)
    print("pgvector Integration Test Suite")
    print("="*60)
    
    results = []
    
    # Test 1: Connection
    try:
        results.append(("Database Connection", await test_database_connection()))
    except Exception as e:
        print(f"\n✗ Test 1 crashed: {e}")
        results.append(("Database Connection", False))
    
    # Test 2: Vector store ops
    try:
        results.append(("Vector Store Ops", await test_vector_store_operations()))
    except Exception as e:
        print(f"\n✗ Test 2 crashed: {e}")
        results.append(("Vector Store Ops", False))
    
    # Test 3: RAG Pipeline
    try:
        results.append(("RAG with pgvector", await test_rag_pipeline_with_pgvector()))
    except Exception as e:
        print(f"\n✗ Test 3 crashed: {e}")
        results.append(("RAG with pgvector", False))
    
    # Test 4: Performance
    try:
        results.append(("Performance Test", await test_performance_comparison()))
    except Exception as e:
        print(f"\n✗ Test 4 crashed: {e}")
        results.append(("Performance Test", False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL/SKIP"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total = len(results)
    print(f"\nTotal: {passed_count}/{total} tests passed")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


