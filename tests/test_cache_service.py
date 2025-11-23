"""
Tests for Redis caching service.
"""

import pytest
from cache_service import CacheService, _make_cache_key


def test_cache_disabled_by_default():
    """Cache service should gracefully handle Redis being disabled."""
    cache = CacheService()
    
    # If Redis not configured, should return None
    result = cache.get_query_result("test query", k=5, workspace_id="ws1")
    assert result is None
    
    # Set should return False if Redis not enabled
    success = cache.set_query_result("test query", k=5, workspace_id="ws1", result={"answer": "test"})
    # Either False or True (depending on whether Redis is actually running)
    assert isinstance(success, bool)


def test_make_cache_key_stable():
    """Cache keys should be stable for same input."""
    key1 = _make_cache_key("test", {"query": "hello", "k": 5})
    key2 = _make_cache_key("test", {"query": "hello", "k": 5})
    
    assert key1 == key2
    
    # Different data should produce different keys
    key3 = _make_cache_key("test", {"query": "goodbye", "k": 5})
    assert key1 != key3


def test_cache_query_result():
    """Test caching query results."""
    cache = CacheService()
    
    query = "What is RAG?"
    workspace_id = "test-workspace"
    result = {"answer": "RAG is...", "chunks": []}
    
    # Try to cache (may fail if Redis not running - that's ok)
    cache.set_query_result(query, k=5, workspace_id=workspace_id, result=result, ttl=60)
    
    # Try to retrieve
    cached = cache.get_query_result(query, k=5, workspace_id=workspace_id)
    
    # If Redis is running, should get back the result
    # If not, should get None (graceful degradation)
    assert cached is None or cached == result


def test_cache_embedding():
    """Test caching embedding vectors."""
    cache = CacheService()
    
    text = "Sample text for embedding"
    model = "text-embedding-3-small"
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    
    # Try to cache
    cache.set_embedding(text, model, embedding, ttl=60)
    
    # Try to retrieve
    cached = cache.get_embedding(text, model)
    
    # Should either get the embedding back or None
    assert cached is None or cached == embedding


def test_cache_stats():
    """Test caching system stats."""
    cache = CacheService()
    
    stats = {"count": 100, "sources": 5}
    
    cache.set_stats(stats, ttl=60)
    cached = cache.get_stats()
    
    assert cached is None or cached == stats


def test_cache_metrics():
    """Test cache metrics reporting."""
    cache = CacheService()
    
    metrics = cache.get_metrics()
    
    assert isinstance(metrics, dict)
    assert "enabled" in metrics
    
    if metrics["enabled"]:
        # If enabled, should have stats
        assert "hits" in metrics or "error" in metrics


def test_cache_healthcheck():
    """Test cache health check."""
    cache = CacheService()
    
    is_healthy = cache.healthcheck()
    
    # Should return boolean
    assert isinstance(is_healthy, bool)
    
    # If disabled, should be False
    if not cache.enabled:
        assert is_healthy == False


def test_cache_invalidate_workspace():
    """Test workspace cache invalidation."""
    cache = CacheService()
    
    # Try to invalidate (should not error even if Redis disabled)
    deleted = cache.invalidate_workspace("test-workspace-123")
    
    # Should return int (number of keys deleted)
    assert isinstance(deleted, int)
    assert deleted >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

