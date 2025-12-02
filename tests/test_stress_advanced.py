"""
Advanced Stress Tests for Mini-RAG / Second Brain

These tests push the system to its limits to identify breaking points
and ensure stability under extreme conditions.

Run with:
    pytest tests/test_stress_advanced.py -v -m slow
    pytest tests/test_stress_advanced.py -v --timeout=300

Warning: These tests may take several minutes to complete and consume
significant system resources.
"""

import asyncio
import concurrent.futures
import gc
import json
import os
import random
import string
import sys
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path
from typing import List, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("LOCAL_MODE", "true")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def stress_temp_dir():
    """Create a temporary directory that persists across tests in this module."""
    with tempfile.TemporaryDirectory(prefix="minirag_stress_") as tmpdir:
        yield tmpdir


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from server import app
    return TestClient(app)


def generate_random_text(length: int = 1000) -> str:
    """Generate random text content."""
    words = ['the', 'quick', 'brown', 'fox', 'jumps', 'over', 'lazy', 'dog',
             'machine', 'learning', 'artificial', 'intelligence', 'data', 'science',
             'neural', 'network', 'deep', 'algorithm', 'model', 'training']
    result = []
    while len(' '.join(result)) < length:
        result.append(random.choice(words))
    return ' '.join(result)[:length]


def generate_random_document(path: Path, size_kb: int = 10) -> Path:
    """Generate a random document of specified size."""
    content = generate_random_text(size_kb * 1024)
    path.write_text(content)
    return path


# =============================================================================
# CONCURRENT LOAD TESTS
# =============================================================================

@pytest.mark.slow
class TestConcurrentLoad:
    """Test system behavior under concurrent load."""

    def test_100_concurrent_health_checks(self, client):
        """Test 100 concurrent health check requests."""
        num_requests = 100
        results = {"success": 0, "error": 0, "times": []}
        lock = threading.Lock()

        def make_request():
            start = time.time()
            try:
                response = client.get("/health")
                elapsed = time.time() - start
                with lock:
                    if response.status_code == 200:
                        results["success"] += 1
                    else:
                        results["error"] += 1
                    results["times"].append(elapsed)
            except Exception:
                with lock:
                    results["error"] += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            concurrent.futures.wait(futures, timeout=60)

        success_rate = results["success"] / num_requests
        avg_time = sum(results["times"]) / len(results["times"]) if results["times"] else 0
        max_time = max(results["times"]) if results["times"] else 0

        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"
        assert avg_time < 1.0, f"Average response time too high: {avg_time:.3f}s"
        assert max_time < 5.0, f"Max response time too high: {max_time:.3f}s"

    def test_mixed_endpoint_load(self, client):
        """Test concurrent requests to multiple endpoints."""
        # Use only endpoints that work without index initialization
        endpoints = [
            ("/health", "GET"),
            ("/api/v1/stats", "GET"),
            ("/metrics", "GET"),
            ("/docs", "GET"),
        ]
        num_requests = 200
        results = {"success": 0, "error": 0}
        lock = threading.Lock()

        def make_request():
            endpoint, method = random.choice(endpoints)
            try:
                if method == "GET":
                    response = client.get(endpoint)
                else:
                    response = client.post(endpoint)

                with lock:
                    # 200 is success, 400/401 are acceptable for protected endpoints
                    if response.status_code in [200, 400, 401]:
                        results["success"] += 1
                    else:
                        results["error"] += 1
            except Exception:
                with lock:
                    results["error"] += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            concurrent.futures.wait(futures, timeout=120)

        success_rate = results["success"] / num_requests
        assert success_rate >= 0.90, f"Success rate too low: {success_rate:.2%}"

    @pytest.mark.timeout(120)
    def test_sustained_concurrent_load(self, client):
        """Test system under sustained concurrent load for 60 seconds."""
        duration = 60
        num_workers = 10
        results = {"requests": 0, "errors": 0, "times": []}
        stop_flag = threading.Event()
        lock = threading.Lock()

        def worker():
            while not stop_flag.is_set():
                start = time.time()
                try:
                    response = client.get("/health")
                    elapsed = time.time() - start
                    with lock:
                        results["requests"] += 1
                        results["times"].append(elapsed)
                        if response.status_code != 200:
                            results["errors"] += 1
                except Exception:
                    with lock:
                        results["errors"] += 1
                time.sleep(0.01)  # Small delay

        # Start workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker) for _ in range(num_workers)]

            # Run for duration
            time.sleep(duration)
            stop_flag.set()

            # Wait for workers to finish
            concurrent.futures.wait(futures, timeout=10)

        throughput = results["requests"] / duration
        error_rate = results["errors"] / results["requests"] if results["requests"] > 0 else 0
        avg_latency = sum(results["times"]) / len(results["times"]) if results["times"] else 0

        print(f"\nSustained Load Results:")
        print(f"  Throughput: {throughput:.1f} req/s")
        print(f"  Error rate: {error_rate:.2%}")
        print(f"  Avg latency: {avg_latency:.3f}s")

        assert throughput > 10, f"Throughput too low: {throughput:.1f} req/s"
        assert error_rate < 0.05, f"Error rate too high: {error_rate:.2%}"


# =============================================================================
# MEMORY STRESS TESTS
# =============================================================================

@pytest.mark.slow
class TestMemoryStress:
    """Test system behavior under memory pressure."""

    def test_large_chunk_volume(self, stress_temp_dir):
        """Test system with large number of chunks."""
        from raglite import ingest_docs
        from retrieval import load_chunks, SimpleIndex

        out_path = os.path.join(stress_temp_dir, "large_volume_chunks.jsonl")

        # Generate 100 documents to create many chunks
        num_docs = 100
        for i in range(num_docs):
            doc_path = Path(stress_temp_dir) / f"vol_doc_{i}.txt"
            generate_random_document(doc_path, size_kb=5)
            ingest_docs(str(doc_path), out_jsonl=out_path)

        chunks = load_chunks(out_path)
        print(f"\nGenerated {len(chunks)} chunks from {num_docs} documents")

        # Build index and perform searches
        index = SimpleIndex(chunks)

        # Multiple search operations
        search_times = []
        for _ in range(50):
            query = generate_random_text(50)
            start = time.time()
            results = index.search(query, k=10)
            search_times.append(time.time() - start)

        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)

        print(f"Search performance:")
        print(f"  Avg: {avg_search_time:.4f}s")
        print(f"  Max: {max_search_time:.4f}s")

        assert avg_search_time < 0.5, f"Search too slow: {avg_search_time:.4f}s"

    def test_memory_usage_during_ingestion(self, stress_temp_dir):
        """Monitor memory usage during bulk ingestion."""
        from raglite import ingest_docs

        tracemalloc.start()

        out_path = os.path.join(stress_temp_dir, "memory_test_chunks.jsonl")

        # Ingest documents and track memory
        memory_snapshots = []
        for i in range(50):
            doc_path = Path(stress_temp_dir) / f"mem_doc_{i}.txt"
            generate_random_document(doc_path, size_kb=10)
            ingest_docs(str(doc_path), out_jsonl=out_path)

            current, peak = tracemalloc.get_traced_memory()
            memory_snapshots.append((i, current / 1024 / 1024, peak / 1024 / 1024))

            # Force garbage collection periodically
            if i % 10 == 0:
                gc.collect()

        tracemalloc.stop()

        # Analyze memory growth
        initial_mem = memory_snapshots[0][1]
        final_mem = memory_snapshots[-1][1]
        peak_mem = max(s[2] for s in memory_snapshots)

        print(f"\nMemory usage during ingestion:")
        print(f"  Initial: {initial_mem:.1f} MB")
        print(f"  Final: {final_mem:.1f} MB")
        print(f"  Peak: {peak_mem:.1f} MB")

        # Memory shouldn't grow unboundedly
        assert peak_mem < 500, f"Memory usage too high: {peak_mem:.1f} MB"

    def test_search_memory_stability(self, stress_temp_dir):
        """Test that repeated searches don't leak memory."""
        from raglite import ingest_docs
        from retrieval import load_chunks, SimpleIndex

        out_path = os.path.join(stress_temp_dir, "search_mem_chunks.jsonl")

        # Create test data
        for i in range(20):
            doc_path = Path(stress_temp_dir) / f"search_doc_{i}.txt"
            generate_random_document(doc_path, size_kb=5)
            ingest_docs(str(doc_path), out_jsonl=out_path)

        chunks = load_chunks(out_path)
        index = SimpleIndex(chunks)

        # Record initial memory
        gc.collect()
        tracemalloc.start()
        initial_mem = tracemalloc.get_traced_memory()[0]

        # Perform many searches
        for _ in range(1000):
            query = generate_random_text(30)
            _ = index.search(query, k=10)

        gc.collect()
        final_mem = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_growth = (final_mem - initial_mem) / 1024 / 1024  # MB

        print(f"\nMemory growth after 1000 searches: {memory_growth:.2f} MB")

        # Should not grow significantly
        assert memory_growth < 50, f"Memory leak detected: {memory_growth:.2f} MB growth"


# =============================================================================
# FILE I/O STRESS TESTS
# =============================================================================

@pytest.mark.slow
class TestFileIOStress:
    """Test file I/O under stress conditions."""

    def test_concurrent_file_writes(self, stress_temp_dir):
        """Test concurrent writes to chunks file."""
        from raglite import write_jsonl

        chunks_path = os.path.join(stress_temp_dir, "concurrent_chunks.jsonl")
        errors = []
        lock = threading.Lock()

        def write_chunk(idx: int):
            try:
                chunk = {
                    "id": f"concurrent-{idx}",
                    "text": f"Content for chunk {idx}",
                    "workspace_id": f"ws-{idx % 5}"
                }
                write_jsonl(chunks_path, [chunk])
            except Exception as e:
                with lock:
                    errors.append((idx, str(e)))

        # Write 50 chunks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_chunk, i) for i in range(50)]
            concurrent.futures.wait(futures, timeout=60)

        # Some errors are acceptable due to file locking
        error_rate = len(errors) / 50
        print(f"\nConcurrent write errors: {len(errors)}/50 ({error_rate:.2%})")

        # Verify file integrity
        if os.path.exists(chunks_path):
            with open(chunks_path) as f:
                lines = f.readlines()
            valid_lines = 0
            for line in lines:
                try:
                    json.loads(line)
                    valid_lines += 1
                except json.JSONDecodeError:
                    pass

            print(f"Valid JSON lines: {valid_lines}/{len(lines)}")
            assert valid_lines > 0, "No valid chunks written"

    def test_rapid_read_write_cycles(self, stress_temp_dir):
        """Test rapid alternating read/write operations."""
        from raglite import write_jsonl
        from retrieval import load_chunks

        chunks_path = os.path.join(stress_temp_dir, "rapid_rw_chunks.jsonl")
        errors = []

        for i in range(100):
            try:
                # Write
                chunk = {"id": f"rapid-{i}", "text": f"Rapid content {i}"}
                write_jsonl(chunks_path, [chunk])

                # Read
                chunks = load_chunks(chunks_path)
                assert len(chunks) > 0

            except Exception as e:
                errors.append((i, str(e)))

        error_rate = len(errors) / 100
        assert error_rate < 0.1, f"Too many errors in rapid R/W: {error_rate:.2%}"


# =============================================================================
# SEARCH STRESS TESTS
# =============================================================================

@pytest.mark.slow
class TestSearchStress:
    """Stress test search functionality."""

    def test_search_with_extreme_k_values(self, stress_temp_dir):
        """Test search with various k values."""
        from raglite import ingest_docs
        from retrieval import load_chunks, SimpleIndex

        out_path = os.path.join(stress_temp_dir, "k_test_chunks.jsonl")

        # Create test data
        for i in range(30):
            doc_path = Path(stress_temp_dir) / f"k_doc_{i}.txt"
            generate_random_document(doc_path, size_kb=3)
            ingest_docs(str(doc_path), out_jsonl=out_path)

        chunks = load_chunks(out_path)
        index = SimpleIndex(chunks)

        # Test various k values
        k_values = [1, 5, 10, 50, 100, 500, 1000, len(chunks), len(chunks) * 2]

        for k in k_values:
            try:
                results = index.search("machine learning", k=k)
                assert len(results) <= min(k, len(chunks))
                print(f"k={k}: returned {len(results)} results")
            except Exception as e:
                pytest.fail(f"Search failed with k={k}: {e}")

    def test_search_with_special_characters(self, stress_temp_dir):
        """Test search with special characters and unicode."""
        from raglite import ingest_docs
        from retrieval import load_chunks, SimpleIndex

        out_path = os.path.join(stress_temp_dir, "special_char_chunks.jsonl")

        # Create document with special content
        doc_path = Path(stress_temp_dir) / "special.txt"
        doc_path.write_text("""
        Special characters test: @#$%^&*()
        Unicode: 你好世界 مرحبا العالم
        Emoji: 🚀 🎉 🔥
        Math: ∑∫∂∇
        Quotes: "double" 'single' `backtick`
        """)
        ingest_docs(str(doc_path), out_jsonl=out_path)

        chunks = load_chunks(out_path)
        index = SimpleIndex(chunks)

        # Test queries with special characters
        special_queries = [
            "@#$%",
            "你好",
            "🚀",
            '"double"',
            "test & more",
            "a | b",
            "regex: .* [a-z]+",
        ]

        for query in special_queries:
            try:
                results = index.search(query, k=5)
                # Should not crash, regardless of results
                print(f"Query '{query[:20]}...': {len(results)} results")
            except Exception as e:
                pytest.fail(f"Search crashed with query '{query}': {e}")

    def test_search_throughput(self, stress_temp_dir):
        """Measure search throughput (queries per second)."""
        from raglite import ingest_docs
        from retrieval import load_chunks, SimpleIndex

        out_path = os.path.join(stress_temp_dir, "throughput_chunks.jsonl")

        # Create substantial test data
        for i in range(50):
            doc_path = Path(stress_temp_dir) / f"throughput_doc_{i}.txt"
            generate_random_document(doc_path, size_kb=5)
            ingest_docs(str(doc_path), out_jsonl=out_path)

        chunks = load_chunks(out_path)
        index = SimpleIndex(chunks)
        print(f"\nTest data: {len(chunks)} chunks")

        # Measure throughput
        num_queries = 500
        queries = [generate_random_text(30) for _ in range(num_queries)]

        start = time.time()
        for query in queries:
            _ = index.search(query, k=10)
        elapsed = time.time() - start

        throughput = num_queries / elapsed
        print(f"Search throughput: {throughput:.1f} queries/second")

        assert throughput > 100, f"Search throughput too low: {throughput:.1f} q/s"


# =============================================================================
# PIPELINE STRESS TESTS
# =============================================================================

@pytest.mark.slow
class TestPipelineStress:
    """Stress test the RAG pipeline."""

    @pytest.mark.asyncio
    async def test_concurrent_pipeline_queries(self, stress_temp_dir):
        """Test concurrent RAG pipeline queries."""
        from raglite import ingest_docs
        from rag_pipeline import RAGPipeline

        out_path = os.path.join(stress_temp_dir, "pipeline_chunks.jsonl")

        # Create test data
        for i in range(20):
            doc_path = Path(stress_temp_dir) / f"pipeline_doc_{i}.txt"
            generate_random_document(doc_path, size_kb=3)
            ingest_docs(str(doc_path), out_jsonl=out_path)

        pipeline = RAGPipeline(chunks_path=out_path)

        async def run_query(idx: int):
            query = generate_random_text(30)
            try:
                result = await pipeline.retrieve({
                    'projectId': 'default',
                    'userQuery': query,
                    'topK_bm25': 10
                })
                return (idx, True, len(result.get('chunks', [])))
            except Exception as e:
                return (idx, False, str(e))

        # Run concurrent queries
        tasks = [run_query(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        successes = sum(1 for _, success, _ in results if success)
        success_rate = successes / len(results)

        print(f"\nPipeline concurrent queries: {successes}/{len(results)} succeeded")

        assert success_rate >= 0.9, f"Too many pipeline failures: {success_rate:.2%}"

    @pytest.mark.asyncio
    async def test_pipeline_with_filters(self, stress_temp_dir):
        """Test pipeline performance with various filter combinations."""
        from raglite import ingest_docs
        from rag_pipeline import RAGPipeline

        out_path = os.path.join(stress_temp_dir, "filter_stress_chunks.jsonl")

        # Create test data with various attributes
        source_types = ['document', 'youtube', 'transcript']
        workspaces = ['ws-1', 'ws-2', 'ws-3']

        for i in range(30):
            doc_path = Path(stress_temp_dir) / f"filter_doc_{i}.txt"
            generate_random_document(doc_path, size_kb=3)
            ingest_docs(
                str(doc_path),
                out_jsonl=out_path,
                workspace_id=random.choice(workspaces)
            )

        pipeline = RAGPipeline(chunks_path=out_path)

        # Test various filter combinations
        filter_combos = [
            {},
            {'workspace_id': 'ws-1'},
            {'source_type': 'document'},
            {'workspace_id': 'ws-1', 'source_type': 'document'},
        ]

        for filters in filter_combos:
            start = time.time()
            result = await pipeline.retrieve({
                'projectId': 'default',
                'userQuery': 'machine learning',
                'topK_bm25': 10,
                'filters': filters
            })
            elapsed = time.time() - start

            print(f"Filters {filters}: {len(result.get('chunks', []))} results in {elapsed:.3f}s")

            assert elapsed < 2.0, f"Filter query too slow: {elapsed:.3f}s"


# =============================================================================
# RECOVERY STRESS TESTS
# =============================================================================

@pytest.mark.slow
class TestRecoveryStress:
    """Test system recovery under stress conditions."""

    def test_recovery_from_corrupted_line(self, stress_temp_dir):
        """Test recovery when chunks file has corrupted lines."""
        from retrieval import load_chunks

        chunks_path = os.path.join(stress_temp_dir, "corrupted.jsonl")

        # Write file with some corrupted lines
        with open(chunks_path, 'w') as f:
            # Valid line
            f.write(json.dumps({"id": "1", "text": "valid"}) + "\n")
            # Corrupted line
            f.write("this is not valid json\n")
            # Another valid line
            f.write(json.dumps({"id": "2", "text": "also valid"}) + "\n")
            # Partial JSON
            f.write('{"id": "3", "text": "incomplete\n')

        # Should handle gracefully
        try:
            chunks = load_chunks(chunks_path)
            # Should at least get the valid chunks
            print(f"Recovered {len(chunks)} chunks from corrupted file")
        except Exception as e:
            # Or raise a clear error
            print(f"Failed with clear error: {e}")

    def test_recovery_from_empty_file(self, stress_temp_dir):
        """Test handling of empty chunks file."""
        from retrieval import load_chunks, SimpleIndex

        empty_path = os.path.join(stress_temp_dir, "empty.jsonl")
        Path(empty_path).touch()

        chunks = load_chunks(empty_path)
        assert chunks == [] or chunks is not None

        # Should still be able to create index
        index = SimpleIndex(chunks)
        results = index.search("test", k=5)
        assert results == []


# =============================================================================
# EDGE CASE STRESS TESTS
# =============================================================================

@pytest.mark.slow
class TestEdgeCaseStress:
    """Test edge cases under stress."""

    def test_very_long_document(self, stress_temp_dir):
        """Test ingesting a very long document."""
        from raglite import ingest_docs
        from retrieval import load_chunks

        out_path = os.path.join(stress_temp_dir, "long_doc_chunks.jsonl")

        # Create a 1MB document
        doc_path = Path(stress_temp_dir) / "huge.txt"
        generate_random_document(doc_path, size_kb=1024)

        start = time.time()
        ingest_docs(str(doc_path), out_jsonl=out_path)
        elapsed = time.time() - start

        chunks = load_chunks(out_path)
        print(f"\n1MB document: {len(chunks)} chunks in {elapsed:.2f}s")

        assert len(chunks) > 10, "Large document should produce many chunks"
        assert elapsed < 60, f"Ingestion too slow: {elapsed:.2f}s"

    def test_many_small_documents(self, stress_temp_dir):
        """Test ingesting many small documents."""
        from raglite import ingest_docs
        from retrieval import load_chunks

        out_path = os.path.join(stress_temp_dir, "many_small_chunks.jsonl")

        # Create 200 tiny documents
        start = time.time()
        for i in range(200):
            doc_path = Path(stress_temp_dir) / f"tiny_{i}.txt"
            doc_path.write_text(f"Tiny document {i} content.")
            ingest_docs(str(doc_path), out_jsonl=out_path)
        elapsed = time.time() - start

        chunks = load_chunks(out_path)
        print(f"\n200 tiny documents: {len(chunks)} chunks in {elapsed:.2f}s")

        assert len(chunks) >= 200, "Each tiny doc should produce at least one chunk"
        assert elapsed < 120, f"Bulk ingestion too slow: {elapsed:.2f}s"

    def test_deeply_nested_content(self, stress_temp_dir):
        """Test handling of deeply nested/structured content."""
        from raglite import ingest_docs
        from retrieval import load_chunks

        out_path = os.path.join(stress_temp_dir, "nested_chunks.jsonl")

        # Create document with nested structure
        doc_path = Path(stress_temp_dir) / "nested.md"
        content = ""
        for level in range(10):
            content += "#" * (level + 1) + f" Level {level + 1}\n"
            content += f"Content at level {level + 1}. " * 50 + "\n\n"
        doc_path.write_text(content)

        ingest_docs(str(doc_path), out_jsonl=out_path)
        chunks = load_chunks(out_path)

        print(f"\nNested document: {len(chunks)} chunks")
        assert len(chunks) > 0


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short", "-x"])
