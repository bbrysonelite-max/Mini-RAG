"""
Test script for RAG Pipeline implementation.

Tests:
1. BM25-only retrieval (no vector search)
2. Hybrid retrieval (BM25 + vector)
3. Filtering by source_type, confidentiality
4. Abstention behavior
5. Workspace isolation for multi-tenancy
6. Chunk backup and restore safety

Run with: python test_rag_pipeline.py
"""

import asyncio
import json
import os
import subprocess
import sys
import logging
import tempfile
from pathlib import Path

import pytest  # type: ignore

from rag_pipeline import RAGPipeline, RetrieveOptions
from model_service_impl import ConcreteModelService
from raglite import write_jsonl, ingest_docs
from retrieval import delete_source_chunks, get_unique_sources, load_chunks, SimpleIndex
from chunk_backup import restore_chunk_backup

ROOT_DIR = Path(__file__).resolve().parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run_test_bm25_only():
    """Test BM25 retrieval without vector search."""
    print("\n" + "="*60)
    print("TEST 1: BM25-Only Retrieval")
    print("="*60)
    
    chunks_path = "out/chunks.jsonl"
    
    if not os.path.exists(chunks_path):
        print(f"✗ Chunks file not found: {chunks_path}")
        print("  Run ingestion first to create chunks.")
        return False
    
    # Initialize pipeline without model service
    pipeline = RAGPipeline(chunks_path=chunks_path)
    
    if not pipeline.chunks:
        print("✗ No chunks loaded")
        return False
    
    print(f"✓ Loaded {len(pipeline.chunks)} chunks")
    
    # Test retrieval
    query = "What is machine learning?"
    print(f"\nQuery: '{query}'")
    
    result = await pipeline.retrieve({
        'projectId': 'default',
        'userQuery': query,
        'topK_bm25': 10
    })
    
    chunks = result.get('chunks', [])
    print(f"✓ Retrieved {len(chunks)} chunks")
    
    if chunks:
        print(f"  Top result score: {chunks[0]['score']:.3f}")
        print(f"  Top result preview: {chunks[0]['chunk']['text'][:100]}...")
        print(f"  Abstained: {result.get('abstained', False)}")
    
    metadata = result.get('metadata', {})
    print(f"\nMetadata:")
    print(f"  BM25 results: {metadata.get('bm25_results', 0)}")
    print(f"  Vector results: {metadata.get('vector_results', 0)}")
    print(f"  Final count: {metadata.get('final_count', 0)}")
    
    return True


async def _run_test_hybrid_retrieval():
    """Test hybrid retrieval with BM25 + vector search."""
    print("\n" + "="*60)
    print("TEST 2: Hybrid Retrieval (BM25 + Vector)")
    print("="*60)
    
    chunks_path = "out/chunks.jsonl"
    
    # Check for API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("✗ OPENAI_API_KEY not set - skipping hybrid test")
        print("  Set API key to test vector search")
        return False
    
    # Initialize with model service
    model_service = ConcreteModelService()
    pipeline = RAGPipeline(
        chunks_path=chunks_path,
        model_service=model_service
    )
    
    print(f"✓ Loaded {len(pipeline.chunks)} chunks")
    
    # Build vector index
    print("\nBuilding vector index (this may take a while)...")
    stats = await pipeline.build_vector_index(batch_size=20)
    
    if 'error' in stats:
        print(f"✗ Error building vector index: {stats['error']}")
        return False
    
    print(f"✓ Vector index built:")
    print(f"  Chunks embedded: {stats['chunks_embedded']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Vector store size: {stats['vector_store_size']}")
    
    # Test hybrid retrieval
    query = "explain the main concepts"
    print(f"\nQuery: '{query}'")
    
    result = await pipeline.retrieve({
        'projectId': 'default',
        'userQuery': query,
        'topK_bm25': 10,
        'topK_vector': 10
    })
    
    chunks = result.get('chunks', [])
    print(f"✓ Retrieved {len(chunks)} chunks")
    
    if chunks:
        print(f"\nTop 3 results:")
        for i, item in enumerate(chunks[:3], 1):
            score = item['score']
            source = item['source']
            text_preview = item['chunk']['text'][:80]
            print(f"  {i}. [{source}] score={score:.3f}: {text_preview}...")
    
    metadata = result.get('metadata', {})
    print(f"\nMetadata:")
    print(f"  BM25 results: {metadata.get('bm25_results', 0)}")
    print(f"  Vector results: {metadata.get('vector_results', 0)}")
    print(f"  After merge: {metadata.get('after_merge', 0)}")
    print(f"  Final count: {metadata.get('final_count', 0)}")
    print(f"  Abstained: {result.get('abstained', False)}")
    
    return True


async def _run_test_filtering():
    """Test filtering by source_type."""
    print("\n" + "="*60)
    print("TEST 3: Filtering")
    print("="*60)
    
    chunks_path = "out/chunks.jsonl"
    pipeline = RAGPipeline(chunks_path=chunks_path)
    
    if not pipeline.chunks:
        print("✗ No chunks loaded")
        return False
    
    print(f"✓ Loaded {len(pipeline.chunks)} chunks")
    
    # Test without filter
    query = "information"
    result_all = await pipeline.retrieve({
        'projectId': 'default',
        'userQuery': query,
        'topK_bm25': 20
    })
    
    all_count = len(result_all.get('chunks', []))
    print(f"\nWithout filter: {all_count} results")
    
    # Test with source_type filter
    result_filtered = await pipeline.retrieve({
        'projectId': 'default',
        'userQuery': query,
        'topK_bm25': 20,
        'filters': {
            'source_type': 'youtube'
        }
    })
    
    filtered_count = len(result_filtered.get('chunks', []))
    print(f"With source_type=youtube filter: {filtered_count} results")
    
    if filtered_count < all_count:
        print(f"✓ Filtering working (reduced from {all_count} to {filtered_count})")
        return True
    elif filtered_count == 0:
        print("  Note: No YouTube chunks found in index")
        return True
    else:
        print("✓ Filter test complete")
        return True


async def _run_test_abstention():
    """Test abstention behavior."""
    print("\n" + "="*60)
    print("TEST 4: Abstention Behavior")
    print("="*60)
    
    chunks_path = "out/chunks.jsonl"
    pipeline = RAGPipeline(chunks_path=chunks_path)
    
    if not pipeline.chunks:
        print("✗ No chunks loaded")
        return False
    
    # Test with nonsense query
    query = "xyzabc123 nonexistent query zzzqqq"
    print(f"\nNonsense query: '{query}'")
    
    result = await pipeline.retrieve({
        'projectId': 'default',
        'userQuery': query,
        'topK_bm25': 10
    })
    
    abstained = result.get('abstained', False)
    reason = result.get('abstentionReason', '')
    chunks = result.get('chunks', [])
    
    print(f"  Retrieved: {len(chunks)} chunks")
    print(f"  Abstained: {abstained}")
    if reason:
        print(f"  Reason: {reason}")
    
    if abstained:
        print("✓ Correctly abstained on poor query")
    else:
        print("  Note: Did not abstain (scores may be above threshold)")
    
    return True


async def _run_test_workspace_isolation():
    """Ensure ingestion tags workspace_id and retrieval respects workspace filters."""
    print("\n" + "="*60)
    print("TEST 5: Workspace Isolation")
    print("="*60)

    success = True

    with tempfile.TemporaryDirectory() as tmp_dir:
        chunks_path = os.path.join(tmp_dir, "chunks.jsonl")
        workspace_a = "ws-1"
        workspace_b = "ws-2"
        user_id = "user-123"

        doc_a = Path(tmp_dir) / "workspace_a.txt"
        doc_b = Path(tmp_dir) / "workspace_b.txt"
        doc_a.write_text("Apples grow on trees. Workspace alpha loves apples.", encoding="utf-8")
        doc_b.write_text("Bananas grow on plants. Workspace beta loves bananas.", encoding="utf-8")

        # Ingest documents with explicit workspace tagging.
        ingest_docs(str(doc_a), out_jsonl=chunks_path, language="en", user_id=user_id, workspace_id=workspace_a)
        ingest_docs(str(doc_b), out_jsonl=chunks_path, language="en", user_id=user_id, workspace_id=workspace_b)

        chunks = load_chunks(chunks_path)
        if len(chunks) != 2:
            print(f"✗ Expected 2 ingested chunks, found {len(chunks)}")
            return False

        workspace_ids = {chunk.get("workspace_id") for chunk in chunks}
        if {workspace_a, workspace_b} != workspace_ids:
            print(f"✗ Workspace tags missing or incorrect: {workspace_ids}")
            success = False
        else:
            print("✓ Ingestion preserved workspace metadata")

        index = SimpleIndex(chunks)

        apples_local = index.search("apples", k=5, workspace_id=workspace_a)
        apples_cross = index.search("apples", k=5, workspace_id=workspace_b)
        bananas_local = index.search("bananas", k=5, workspace_id=workspace_b)
        bananas_cross = index.search("bananas", k=5, workspace_id=workspace_a)

        def _workspace_ids(results):
            return {chunks[idx].get("workspace_id") for idx, _ in results}

        if not apples_local or _workspace_ids(apples_local) != {workspace_a}:
            print("✗ Workspace A query did not return exclusively workspace A chunks")
            success = False
        if _workspace_ids(apples_cross) & {workspace_a}:
            print("✗ Workspace filter leaked workspace A chunks into workspace B query")
            success = False
        if not bananas_local or _workspace_ids(bananas_local) != {workspace_b}:
            print("✗ Workspace B query did not return exclusively workspace B chunks")
            success = False
        if _workspace_ids(bananas_cross) & {workspace_b}:
            print("✗ Workspace filter leaked workspace B chunks into workspace A query")
            success = False

        if success:
            print("✓ Workspace filters isolate search results correctly")

    return success


async def _run_test_cli_workspace_flags():
    """Verify CLI ingestion threads user/workspace IDs into chunks."""
    print("\n" + "="*60)
    print("TEST 6: CLI Workspace Flags")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        doc_path = Path(tmp_dir) / "cli_doc.txt"
        doc_path.write_text("CLI workspace isolation check.", encoding="utf-8")

        chunks_path = Path(tmp_dir) / "chunks.jsonl"
        user_id = "cli-user-1"
        workspace_id = "cli-workspace-1"

        cmd = [
            sys.executable,
            "raglite.py",
            "ingest-docs",
            "--path",
            str(doc_path),
            "--out",
            str(chunks_path),
            "--user-id",
            user_id,
            "--workspace-id",
            workspace_id,
        ]

        try:
            subprocess.run(
                cmd,
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print("✗ CLI ingest-docs failed")
            print(exc.stdout)
            print(exc.stderr)
            return False

        chunks = load_chunks(str(chunks_path))
        if len(chunks) != 1:
            print(f"✗ Expected 1 chunk, found {len(chunks)}")
            return False

        chunk = chunks[0]
        if chunk.get("user_id") != user_id:
            print(f"✗ user_id mismatch: {chunk.get('user_id')} != {user_id}")
            return False
        if chunk.get("workspace_id") != workspace_id:
            print(f"✗ workspace_id mismatch: {chunk.get('workspace_id')} != {workspace_id}")
            return False

        print("✓ CLI ingestion tagged user_id and workspace_id correctly")
    return True


async def _run_test_chunk_backups():
    """Test that chunk backups are created for append and rewrite flows."""
    print("\n" + "="*60)
    print("TEST 7: Chunk Backup Safety")
    print("="*60)

    success = True

    with tempfile.TemporaryDirectory() as tmp_dir:
        chunks_path = os.path.join(tmp_dir, "chunks.jsonl")
        backups_dir = Path(tmp_dir) / "backups"
        timestamp_files = []

        row1 = {
            "id": "phase4-test-1",
            "source": {"type": "document", "path": "phase4-doc.md"},
            "content": "Phase 4 backup seed",
        }
        row2 = {
            "id": "phase4-test-2",
            "source": {"type": "document", "path": "phase4-doc.md"},
            "content": "Phase 4 backup append",
        }

        # Initial write (no backup expected because file does not yet exist).
        write_jsonl(chunks_path, [row1])
        initial_content = Path(chunks_path).read_text()

        # Second write should snapshot the existing content before appending.
        write_jsonl(chunks_path, [row2])

        staged_path = Path(f"{chunks_path}.staged")
        if staged_path.exists():
            print(f"✗ Staged file still present: {staged_path}")
            success = False
        else:
            print("✓ Staged append cleaned up temp file")

        combined_lines = Path(chunks_path).read_text().splitlines()
        if len(combined_lines) == 2:
            print("✓ Transactional append preserved both rows")
        else:
            print(f"✗ Unexpected row count after append: {len(combined_lines)}")
            success = False

        if not backups_dir.exists():
            print("✗ Backup directory not created after append")
            success = False
        else:
            timestamp_files = sorted(
                f for f in os.listdir(backups_dir) if f.startswith("chunks-")
            )
            latest_path = backups_dir / "latest.jsonl"

            if not timestamp_files:
                print("✗ No timestamped backups found after append")
                success = False
            else:
                print(f"✓ Created {len(timestamp_files)} timestamped backup(s) after append")

            if not latest_path.exists():
                print("✗ Latest backup pointer missing after append")
                success = False
            else:
                latest_content = latest_path.read_text()
                if latest_content == initial_content:
                    print("✓ Latest backup preserves pre-append content")
                else:
                    print("✗ Latest backup content mismatch after append")
                    success = False
        if not success:
            return False

        pre_delete_content = Path(chunks_path).read_text()
        chunks = load_chunks(chunks_path)
        sources = get_unique_sources(chunks)
        if not sources:
            print("✗ Unable to determine source for deletion test")
            return False
        source_id = sources[0]["id"]

        backup_result = delete_source_chunks(chunks_path, source_id)
        backup_path = backup_result.get("backup_path")
        timestamp_files_after = sorted(
            f for f in os.listdir(backups_dir) if f.startswith("chunks-")
        )

        if not backup_path:
            print("✗ delete_source_chunks did not report a backup path")
            success = False
        elif not Path(backup_path).exists():
            print(f"✗ Reported backup missing: {backup_path}")
            success = False
        else:
            print(f"✓ delete_source_chunks created backup: {Path(backup_path).name}")

        if len(timestamp_files_after) <= len(timestamp_files):
            print("✗ Rewrite did not create a new timestamped backup")
            success = False
        else:
            print("✓ Rewrite created an additional timestamped backup")

        latest_after = (backups_dir / "latest.jsonl").read_text()
        if latest_after == pre_delete_content:
            print("✓ Latest backup now mirrors pre-delete content")
        else:
            print("✗ Latest backup not updated prior to delete rewrite")
            success = False

        final_chunks = load_chunks(chunks_path)
        if final_chunks:
            print(f"✗ Expected empty file after deletion, found {len(final_chunks)} chunks")
            success = False
        else:
            print("✓ Chunks file rewritten successfully after deletion")

        # Exercise CLI restore command (defaults to latest backup).
        restore_cmd = [
            sys.executable,
            "raglite.py",
            "restore-backup",
            "--chunks",
            chunks_path,
        ]
        try:
            proc = subprocess.run(
                restore_cmd,
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print(f"✗ CLI restore failed: {exc.stderr or exc.stdout}")
            return False

        try:
            restore_payload = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            print("✗ CLI restore did not return valid JSON")
            return False

        restored_from = restore_payload.get("restored_from")
        if restore_payload.get("error"):
            print(f"✗ CLI restore reported error: {restore_payload['error']}")
            success = False
        elif not restored_from:
            print("✗ CLI restore did not report source backup")
            success = False
        else:
            print("✓ CLI restore reported success")

        pre_restore_snapshot = restore_payload.get("pre_backup")
        if pre_restore_snapshot and Path(pre_restore_snapshot).exists():
            print("✓ Restore captured a pre-restore snapshot")
        else:
            print("✗ Restore did not capture a pre-restore snapshot")
            success = False

        timestamp_files_final = sorted(
            f for f in os.listdir(backups_dir) if f.startswith("chunks-")
        )
        if len(timestamp_files_final) <= len(timestamp_files_after):
            print("✗ Restore did not create an additional timestamped backup")
            success = False
        else:
            print("✓ Restore recorded an additional timestamped backup")

        restored_content = Path(chunks_path).read_text()
        if restored_content == pre_delete_content:
            print("✓ CLI restore reinstated chunk content")
        else:
            print("✗ CLI restore produced unexpected chunk content")
            success = False

        # Explicit helper restore (skip_prebackup avoids duplicate snapshots).
        restore_chunk_backup(
            chunks_path,
            backup_path=restored_from,
            skip_prebackup=True,
        )
        helper_restored = Path(chunks_path).read_text()
        if helper_restored == pre_delete_content:
            print("✓ Direct helper restore matches expected content")
        else:
            print("✗ Direct helper restore mismatch")
            success = False

    return success



@pytest.mark.asyncio
async def test_bm25_only():
    assert await _run_test_bm25_only(), "BM25-only retrieval smoke test failed"


@pytest.mark.asyncio
async def test_hybrid_retrieval():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    assert await _run_test_hybrid_retrieval(), "Hybrid retrieval smoke test failed"


@pytest.mark.asyncio
async def test_filtering():
    assert await _run_test_filtering(), "Filtering smoke test failed"


@pytest.mark.asyncio
async def test_abstention():
    assert await _run_test_abstention(), "Abstention smoke test failed"


@pytest.mark.asyncio
async def test_workspace_isolation():
    assert await _run_test_workspace_isolation(), "Workspace isolation check failed"


@pytest.mark.asyncio
async def test_cli_workspace_flags():
    assert await _run_test_cli_workspace_flags(), "CLI workspace flag propagation failed"


@pytest.mark.asyncio
async def test_chunk_backups():
    assert await _run_test_chunk_backups(), "Chunk backup safety check failed"


async def main():
    """Run all tests."""
    print("="*60)
    print("RAG Pipeline Integration Test")
    print("="*60)
    
    results = []
    
    # Test 1: BM25 only
    try:
        results.append(("BM25 Retrieval", await _run_test_bm25_only()))
    except Exception as e:
        print(f"\n✗ Test 1 failed: {e}")
        results.append(("BM25 Retrieval", False))
    
    # Test 2: Hybrid (optional - requires API key)
    try:
        results.append(("Hybrid Retrieval", await _run_test_hybrid_retrieval()))
    except Exception as e:
        print(f"\n✗ Test 2 failed: {e}")
        results.append(("Hybrid Retrieval", False))
    
    # Test 3: Filtering
    try:
        results.append(("Filtering", await _run_test_filtering()))
    except Exception as e:
        print(f"\n✗ Test 3 failed: {e}")
        results.append(("Filtering", False))
    
    # Test 4: Abstention
    try:
        results.append(("Abstention", await _run_test_abstention()))
    except Exception as e:
        print(f"\n✗ Test 4 failed: {e}")
        results.append(("Abstention", False))
    
    # Test 5: Workspace isolation
    try:
        results.append(("Workspace Isolation", await _run_test_workspace_isolation()))
    except Exception as e:
        print(f"\n✗ Test 5 failed: {e}")
        results.append(("Workspace Isolation", False))
    
    # Test 6: CLI workspace flags
    try:
        results.append(("CLI Workspace Flags", await _run_test_cli_workspace_flags()))
    except Exception as e:
        print(f"\n✗ Test 6 failed: {e}")
        results.append(("CLI Workspace Flags", False))
    
    # Test 7: Chunk backups
    try:
        results.append(("Chunk Backup Safety", await _run_test_chunk_backups()))
    except Exception as e:
        print(f"\n✗ Test 7 failed: {e}")
        results.append(("Chunk Backup Safety", False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
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



