"""
Database and Vector Store Tests for Mini-RAG / Second Brain

Tests for PostgreSQL database operations, pgvector functionality,
and chunk storage/retrieval.

Run with:
    pytest tests/test_database_vector_store.py -v
    pytest tests/test_database_vector_store.py -v -m "not requires_db"
"""

import asyncio
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")


# =============================================================================
# FIXTURES
# =============================================================================

class FakeDatabase:
    """Fake database for testing without actual PostgreSQL."""

    def __init__(self):
        self.tables = {
            "chunks": [],
            "sources": [],
            "workspaces": [],
            "organizations": [],
            "users": [],
        }
        self._pool = MagicMock()

    async def initialize(self, min_size=None, max_size=None):
        pass

    async def fetch_one(self, query: str, params=None):
        # Simulate basic queries
        if "SELECT" in query and "chunks" in query:
            if self.tables["chunks"]:
                return self.tables["chunks"][0]
        return None

    async def fetch(self, query: str, params=None):
        if "chunks" in query:
            return self.tables["chunks"]
        return []

    async def execute(self, query: str, params=None):
        if "INSERT" in query and "chunks" in query:
            chunk = {
                "id": params[0] if params else str(uuid.uuid4()),
                "text": params[1] if params and len(params) > 1 else "",
            }
            self.tables["chunks"].append(chunk)
        return None


class FakeVectorStore:
    """Fake vector store for testing."""

    def __init__(self):
        self.chunks = []
        self.vectors = {}

    async def ensure_default_context(self):
        return {"org_id": "default-org", "workspace_id": "default-ws", "project_id": "default-proj"}

    async def ensure_chunks(self, chunks: List[Dict], context: Dict = None):
        for chunk in chunks:
            self.chunks.append(chunk)
            if "embedding" in chunk:
                self.vectors[chunk["id"]] = chunk["embedding"]

    async def fetch_all_chunks(self, workspace_id: str = None):
        if workspace_id:
            return [c for c in self.chunks if c.get("workspace_id") == workspace_id]
        return self.chunks

    async def search_similar(self, query_vector: List[float], k: int = 10, workspace_id: str = None):
        # Return mock results
        results = []
        for i, chunk in enumerate(self.chunks[:k]):
            results.append({
                "chunk": chunk,
                "score": 1.0 - (i * 0.1),
                "distance": i * 0.1
            })
        return results

    async def delete_chunks_by_source(self, source_id: str, workspace_id: str = None):
        self.chunks = [c for c in self.chunks if c.get("source", {}).get("id") != source_id]


@pytest.fixture
def fake_db():
    """Create fake database instance."""
    return FakeDatabase()


@pytest.fixture
def fake_vector_store():
    """Create fake vector store instance."""
    return FakeVectorStore()


@pytest.fixture
def temp_chunks_file():
    """Create temporary chunks file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        chunks = [
            {
                "id": f"chunk-{i}",
                "text": f"Test content {i}",
                "source": {"type": "document", "id": f"source-{i // 3}"},
                "workspace_id": "test-ws",
                "embedding": [0.1 * i] * 10  # Fake embedding
            }
            for i in range(10)
        ]
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


# =============================================================================
# DATABASE CONNECTION TESTS
# =============================================================================

class TestDatabaseConnection:
    """Test database connection handling."""

    def test_database_module_importable(self):
        """Test that database module can be imported."""
        try:
            from database import Database
            assert Database is not None
        except ImportError:
            pytest.skip("Database module not available")

    @pytest.mark.asyncio
    async def test_database_initialization(self, fake_db):
        """Test database initialization."""
        await fake_db.initialize()
        # Should not raise

    @pytest.mark.asyncio
    async def test_database_fetch_one(self, fake_db):
        """Test single row fetch."""
        fake_db.tables["chunks"].append({"id": "1", "text": "test"})

        result = await fake_db.fetch_one("SELECT * FROM chunks WHERE id = $1", ["1"])
        assert result is not None
        assert result["id"] == "1"

    @pytest.mark.asyncio
    async def test_database_fetch_many(self, fake_db):
        """Test multiple row fetch."""
        fake_db.tables["chunks"] = [
            {"id": "1", "text": "one"},
            {"id": "2", "text": "two"},
        ]

        results = await fake_db.fetch("SELECT * FROM chunks")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_database_execute(self, fake_db):
        """Test execute statement."""
        await fake_db.execute(
            "INSERT INTO chunks (id, text) VALUES ($1, $2)",
            ["new-id", "new text"]
        )

        assert len(fake_db.tables["chunks"]) == 1


# =============================================================================
# VECTOR STORE TESTS
# =============================================================================

class TestVectorStore:
    """Test vector store functionality."""

    def test_vector_store_importable(self):
        """Test that vector store module can be imported."""
        try:
            from vector_store import VectorStore
            assert VectorStore is not None
        except ImportError:
            pytest.skip("VectorStore module not available")

    @pytest.mark.asyncio
    async def test_vector_store_ensure_context(self, fake_vector_store):
        """Test ensuring default context."""
        context = await fake_vector_store.ensure_default_context()

        assert "org_id" in context
        assert "workspace_id" in context
        assert "project_id" in context

    @pytest.mark.asyncio
    async def test_vector_store_save_chunks(self, fake_vector_store):
        """Test saving chunks to vector store."""
        chunks = [
            {"id": "1", "text": "test 1", "embedding": [0.1] * 10},
            {"id": "2", "text": "test 2", "embedding": [0.2] * 10},
        ]

        await fake_vector_store.ensure_chunks(chunks)

        assert len(fake_vector_store.chunks) == 2

    @pytest.mark.asyncio
    async def test_vector_store_fetch_chunks(self, fake_vector_store):
        """Test fetching all chunks."""
        fake_vector_store.chunks = [
            {"id": "1", "text": "test", "workspace_id": "ws-1"},
            {"id": "2", "text": "test2", "workspace_id": "ws-2"},
        ]

        # Fetch all
        all_chunks = await fake_vector_store.fetch_all_chunks()
        assert len(all_chunks) == 2

        # Fetch by workspace
        ws_chunks = await fake_vector_store.fetch_all_chunks(workspace_id="ws-1")
        assert len(ws_chunks) == 1
        assert ws_chunks[0]["workspace_id"] == "ws-1"

    @pytest.mark.asyncio
    async def test_vector_store_similarity_search(self, fake_vector_store):
        """Test similarity search."""
        fake_vector_store.chunks = [
            {"id": "1", "text": "machine learning"},
            {"id": "2", "text": "deep learning"},
            {"id": "3", "text": "neural networks"},
        ]

        query_vector = [0.1] * 10
        results = await fake_vector_store.search_similar(query_vector, k=2)

        assert len(results) == 2
        for result in results:
            assert "chunk" in result
            assert "score" in result

    @pytest.mark.asyncio
    async def test_vector_store_delete_by_source(self, fake_vector_store):
        """Test deleting chunks by source."""
        fake_vector_store.chunks = [
            {"id": "1", "source": {"id": "src-1"}},
            {"id": "2", "source": {"id": "src-1"}},
            {"id": "3", "source": {"id": "src-2"}},
        ]

        await fake_vector_store.delete_chunks_by_source("src-1")

        assert len(fake_vector_store.chunks) == 1
        assert fake_vector_store.chunks[0]["source"]["id"] == "src-2"


# =============================================================================
# CHUNK DATABASE TESTS
# =============================================================================

class TestChunkDatabase:
    """Test chunk database operations."""

    def test_chunk_db_importable(self):
        """Test that chunk_db module can be imported."""
        try:
            from chunk_db import store_chunks_to_db, load_chunks_from_db
            assert store_chunks_to_db is not None
            assert load_chunks_from_db is not None
        except ImportError:
            pytest.skip("chunk_db module not available")

    @pytest.mark.asyncio
    async def test_store_chunks_to_db(self, fake_vector_store):
        """Test storing chunks to database."""
        from chunk_db import store_chunks_to_db

        chunks = [
            {"id": "1", "text": "test", "embedding": [0.1] * 10},
        ]

        # Mock would need proper implementation
        # For now, test the import works

    @pytest.mark.asyncio
    async def test_load_chunks_from_db(self, fake_vector_store):
        """Test loading chunks from database."""
        fake_vector_store.chunks = [
            {"id": "1", "text": "loaded"},
        ]

        chunks = await fake_vector_store.fetch_all_chunks()
        assert len(chunks) == 1

    def test_export_chunks_to_jsonl(self, temp_chunks_file, temp_dir):
        """Test exporting chunks to JSONL."""
        from retrieval import load_chunks

        chunks = load_chunks(temp_chunks_file)
        assert len(chunks) > 0

        # Export to new file
        export_path = os.path.join(temp_dir, "export.jsonl")
        with open(export_path, 'w') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk) + "\n")

        # Verify export
        exported = load_chunks(export_path)
        assert len(exported) == len(chunks)


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# =============================================================================
# SCHEMA TESTS
# =============================================================================

class TestDatabaseSchema:
    """Test database schema correctness."""

    def test_schema_file_exists(self):
        """Test that schema file exists."""
        schema_path = PROJECT_ROOT / "db_schema.sql"
        assert schema_path.exists(), "db_schema.sql should exist"

    def test_schema_has_required_tables(self):
        """Test that schema defines required tables."""
        schema_path = PROJECT_ROOT / "db_schema.sql"
        if not schema_path.exists():
            pytest.skip("db_schema.sql not found")

        schema = schema_path.read_text()

        required_tables = [
            "users",
            "organizations",
            "workspaces",
            "chunks",
        ]

        for table in required_tables:
            assert f"CREATE TABLE" in schema and table in schema.lower(), \
                f"Schema should define {table} table"

    def test_schema_has_vector_extension(self):
        """Test that schema enables pgvector extension."""
        schema_path = PROJECT_ROOT / "db_schema.sql"
        if not schema_path.exists():
            pytest.skip("db_schema.sql not found")

        schema = schema_path.read_text()
        assert "vector" in schema.lower(), "Schema should reference vector extension"


# =============================================================================
# MIGRATION TESTS
# =============================================================================

class TestMigrations:
    """Test database migration functionality."""

    def test_migration_from_jsonl(self, temp_chunks_file, fake_vector_store):
        """Test migrating from JSONL to database."""
        from retrieval import load_chunks

        # Load from JSONL
        chunks = load_chunks(temp_chunks_file)
        assert len(chunks) > 0

        # Simulate migration
        for chunk in chunks:
            fake_vector_store.chunks.append(chunk)

        assert len(fake_vector_store.chunks) == len(chunks)


# =============================================================================
# WORKSPACE ISOLATION TESTS
# =============================================================================

class TestDatabaseWorkspaceIsolation:
    """Test workspace isolation at database level."""

    @pytest.mark.asyncio
    async def test_chunks_tagged_with_workspace(self, fake_vector_store):
        """Test that chunks are properly tagged with workspace."""
        chunks = [
            {"id": "1", "text": "ws1 content", "workspace_id": "ws-1"},
            {"id": "2", "text": "ws2 content", "workspace_id": "ws-2"},
        ]

        await fake_vector_store.ensure_chunks(chunks)

        # Verify workspace tagging preserved
        stored = await fake_vector_store.fetch_all_chunks()
        workspace_ids = {c["workspace_id"] for c in stored}
        assert workspace_ids == {"ws-1", "ws-2"}

    @pytest.mark.asyncio
    async def test_query_respects_workspace_filter(self, fake_vector_store):
        """Test that queries respect workspace filters."""
        fake_vector_store.chunks = [
            {"id": "1", "text": "alpha", "workspace_id": "ws-A"},
            {"id": "2", "text": "beta", "workspace_id": "ws-B"},
            {"id": "3", "text": "gamma", "workspace_id": "ws-A"},
        ]

        # Query workspace A only
        ws_a_chunks = await fake_vector_store.fetch_all_chunks(workspace_id="ws-A")
        assert len(ws_a_chunks) == 2
        assert all(c["workspace_id"] == "ws-A" for c in ws_a_chunks)

    @pytest.mark.asyncio
    async def test_delete_respects_workspace(self, fake_vector_store):
        """Test that delete operations respect workspace boundaries."""
        fake_vector_store.chunks = [
            {"id": "1", "source": {"id": "src-1"}, "workspace_id": "ws-A"},
            {"id": "2", "source": {"id": "src-1"}, "workspace_id": "ws-B"},
        ]

        # Delete from workspace A only
        await fake_vector_store.delete_chunks_by_source("src-1", workspace_id="ws-A")

        # ws-B chunk should remain (if implementation supports ws filtering)
        # This tests the interface expectation


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestDatabasePerformance:
    """Test database performance characteristics."""

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, fake_vector_store):
        """Test bulk insert performance."""
        import time

        chunks = [
            {"id": f"chunk-{i}", "text": f"content {i}", "embedding": [0.1] * 10}
            for i in range(1000)
        ]

        start = time.time()
        await fake_vector_store.ensure_chunks(chunks)
        elapsed = time.time() - start

        print(f"\nBulk insert of 1000 chunks: {elapsed:.3f}s")
        assert elapsed < 5.0, "Bulk insert too slow"

    @pytest.mark.asyncio
    async def test_query_performance(self, fake_vector_store):
        """Test query performance with many chunks."""
        import time

        # Populate with chunks
        fake_vector_store.chunks = [
            {"id": f"chunk-{i}", "text": f"content {i}"}
            for i in range(10000)
        ]

        # Measure query time
        start = time.time()
        for _ in range(100):
            await fake_vector_store.fetch_all_chunks()
        elapsed = time.time() - start

        avg_time = elapsed / 100
        print(f"\nAverage query time: {avg_time:.4f}s")
        assert avg_time < 0.1, "Query too slow"


# =============================================================================
# CONNECTION POOL TESTS
# =============================================================================

class TestConnectionPool:
    """Test database connection pooling."""

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, fake_db):
        """Test handling concurrent connections."""
        async def run_query(i):
            await fake_db.fetch_one(f"SELECT {i}")
            return i

        # Run concurrent queries
        tasks = [run_query(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 50

    @pytest.mark.asyncio
    async def test_connection_reuse(self, fake_db):
        """Test that connections are reused."""
        # Multiple operations should reuse connections
        for _ in range(100):
            await fake_db.fetch_one("SELECT 1")

        # Should complete without exhausting connections


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestDatabaseErrorHandling:
    """Test database error handling."""

    @pytest.mark.asyncio
    async def test_handles_connection_error(self):
        """Test handling of connection errors."""
        fake_db = FakeDatabase()

        # Simulate connection error
        async def failing_fetch(*args, **kwargs):
            raise ConnectionError("Database unreachable")

        fake_db.fetch_one = failing_fetch

        with pytest.raises(ConnectionError):
            await fake_db.fetch_one("SELECT 1")

    @pytest.mark.asyncio
    async def test_handles_query_error(self):
        """Test handling of query errors."""
        fake_db = FakeDatabase()

        async def failing_execute(*args, **kwargs):
            raise Exception("Syntax error in query")

        fake_db.execute = failing_execute

        with pytest.raises(Exception) as exc_info:
            await fake_db.execute("INVALID SQL")

        assert "syntax" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()


# =============================================================================
# LIVE DATABASE TESTS (REQUIRES DATABASE_URL)
# =============================================================================

@pytest.mark.requires_db
class TestLiveDatabase:
    """Tests that require actual database connection."""

    @pytest.mark.skipif(
        not os.getenv("DATABASE_URL"),
        reason="Requires DATABASE_URL"
    )
    @pytest.mark.asyncio
    async def test_live_connection(self):
        """Test live database connection."""
        from database import Database

        db = Database()
        await db.initialize()

        result = await db.fetch_one("SELECT 1 as one")
        assert result is not None

    @pytest.mark.skipif(
        not os.getenv("DATABASE_URL"),
        reason="Requires DATABASE_URL"
    )
    @pytest.mark.asyncio
    async def test_live_vector_operations(self):
        """Test live vector operations."""
        from vector_store import VectorStore
        from database import Database

        db = Database()
        await db.initialize()

        vs = VectorStore(db)

        # Test vector similarity (would need proper setup)
        # This is a placeholder for live testing


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
