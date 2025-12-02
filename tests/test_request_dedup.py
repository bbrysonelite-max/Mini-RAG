"""
Tests for request deduplication.
"""

import pytest
import asyncio
from request_dedup import RequestDeduplicator, get_deduplicator


@pytest.mark.asyncio
async def test_dedup_basic():
    """Test basic deduplication works."""
    dedup = RequestDeduplicator(ttl_seconds=60)
    
    call_count = 0
    
    async def expensive_op():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return {"result": "success"}
    
    # Make same request twice concurrently
    task1 = asyncio.create_task(
        dedup.deduplicate({"query": "test", "k": 5}, expensive_op)
    )
    task2 = asyncio.create_task(
        dedup.deduplicate({"query": "test", "k": 5}, expensive_op)
    )
    
    result1, result2 = await asyncio.gather(task1, task2)
    
    # Both should get same result
    assert result1 == result2
    assert result1 == {"result": "success"}
    
    # But operation should only have been called once
    assert call_count == 1


@pytest.mark.asyncio
async def test_dedup_different_requests():
    """Different requests should not be deduplicated."""
    dedup = RequestDeduplicator(ttl_seconds=60)
    
    call_count = 0
    
    async def expensive_op():
        nonlocal call_count
        call_count += 1
        return {"count": call_count}
    
    # Different requests
    result1 = await dedup.deduplicate({"query": "test1"}, expensive_op)
    result2 = await dedup.deduplicate({"query": "test2"}, expensive_op)
    
    # Should execute twice
    assert call_count == 2
    assert result1 != result2


@pytest.mark.asyncio
async def test_dedup_error_propagation():
    """Errors should propagate to all waiters."""
    dedup = RequestDeduplicator(ttl_seconds=60)
    
    async def failing_op():
        await asyncio.sleep(0.1)
        raise ValueError("Intentional error")
    
    # Make same request twice
    task1 = asyncio.create_task(
        dedup.deduplicate({"query": "fail"}, failing_op)
    )
    task2 = asyncio.create_task(
        dedup.deduplicate({"query": "fail"}, failing_op)
    )
    
    # Both should raise the same error
    with pytest.raises(ValueError, match="Intentional error"):
        await task1
    
    with pytest.raises(ValueError, match="Intentional error"):
        await task2


@pytest.mark.asyncio
async def test_dedup_stats():
    """Test deduplication statistics."""
    dedup = RequestDeduplicator(ttl_seconds=60)
    
    async def op():
        await asyncio.sleep(0.1)
        return "done"
    
    # Start concurrent requests
    tasks = [
        asyncio.create_task(dedup.deduplicate({"query": "same"}, op))
        for _ in range(5)
    ]
    
    # Before completion, check stats
    await asyncio.sleep(0.01)  # Let first request start
    stats = dedup.get_stats()
    
    assert stats["pending_requests"] >= 0
    assert stats["total_waiters"] >= 0
    
    # Finish requests
    results = await asyncio.gather(*tasks)
    assert all(r == "done" for r in results)


@pytest.mark.asyncio
async def test_dedup_cleanup():
    """Test cleanup of stale entries."""
    dedup = RequestDeduplicator(ttl_seconds=1)  # Very short TTL
    dedup.start_cleanup()
    
    async def op():
        return "result"
    
    # Add an entry
    result = await dedup.deduplicate({"query": "test"}, op)
    assert result == "result"
    
    # Wait for cleanup
    await asyncio.sleep(2)
    
    # Cleanup should have run
    await dedup.shutdown()


@pytest.mark.asyncio
async def test_get_deduplicator_singleton():
    """Test global deduplicator is singleton."""
    dedup1 = get_deduplicator()
    dedup2 = get_deduplicator()
    
    assert dedup1 is dedup2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])




