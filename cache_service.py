"""
Redis-based caching service for query results and embeddings.
Reduces latency and external API costs by caching expensive operations.
"""

import logging
import hashlib
import json
import os
from typing import Optional, Any, Dict, List
from datetime import timedelta

logger = logging.getLogger("rag")

# Redis is optional - gracefully degrade if not available
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Cache TTLs
QUERY_CACHE_TTL = int(os.getenv("QUERY_CACHE_TTL", "3600"))  # 1 hour
EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL", "86400"))  # 24 hours
STATS_CACHE_TTL = int(os.getenv("STATS_CACHE_TTL", "300"))  # 5 minutes

# Import redis only if enabled
redis_client = None
if REDIS_ENABLED:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        # Test connection
        redis_client.ping()
        logger.info(f"Redis cache enabled: {REDIS_URL}")
    except ImportError:
        logger.warning("Redis enabled but redis package not installed. Run: pip install redis")
        REDIS_ENABLED = False
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Cache disabled.")
        REDIS_ENABLED = False
        redis_client = None


def _make_cache_key(prefix: str, data: Any) -> str:
    """Generate a stable cache key from arbitrary data."""
    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True)
    else:
        serialized = str(data)
    
    hash_obj = hashlib.sha256(serialized.encode())
    return f"{prefix}:{hash_obj.hexdigest()[:16]}"


class CacheService:
    """Redis-backed cache with graceful degradation."""
    
    def __init__(self):
        self.enabled = REDIS_ENABLED
        self.client = redis_client
    
    def get_query_result(self, query: str, k: int, workspace_id: str) -> Optional[Dict]:
        """Get cached query result."""
        if not self.enabled:
            return None
        
        try:
            cache_key = _make_cache_key("query", {
                "query": query.lower().strip(),
                "k": k,
                "workspace_id": workspace_id
            })
            
            cached = self.client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached)
            
            logger.debug(f"Cache miss: {cache_key}")
            return None
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None
    
    def set_query_result(
        self,
        query: str,
        k: int,
        workspace_id: str,
        result: Dict,
        ttl: int = QUERY_CACHE_TTL
    ) -> bool:
        """Cache a query result."""
        if not self.enabled:
            return False
        
        try:
            cache_key = _make_cache_key("query", {
                "query": query.lower().strip(),
                "k": k,
                "workspace_id": workspace_id
            })
            
            self.client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )
            logger.debug(f"Cached query result: {cache_key} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
            return False
    
    def get_embedding(self, text: str, model: str) -> Optional[List[float]]:
        """Get cached embedding vector."""
        if not self.enabled:
            return None
        
        try:
            cache_key = _make_cache_key("embedding", {
                "text": text[:500],  # Truncate for key generation
                "model": model
            })
            
            cached = self.client.get(cache_key)
            if cached:
                logger.debug(f"Embedding cache hit: {cache_key}")
                return json.loads(cached)
            
            return None
        except Exception as e:
            logger.warning(f"Embedding cache get failed: {e}")
            return None
    
    def set_embedding(
        self,
        text: str,
        model: str,
        embedding: List[float],
        ttl: int = EMBEDDING_CACHE_TTL
    ) -> bool:
        """Cache an embedding vector."""
        if not self.enabled:
            return False
        
        try:
            cache_key = _make_cache_key("embedding", {
                "text": text[:500],
                "model": model
            })
            
            self.client.setex(
                cache_key,
                ttl,
                json.dumps(embedding)
            )
            logger.debug(f"Cached embedding: {cache_key} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Embedding cache set failed: {e}")
            return False
    
    def get_stats(self) -> Optional[Dict]:
        """Get cached system stats."""
        if not self.enabled:
            return None
        
        try:
            cached = self.client.get("stats:system")
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.warning(f"Stats cache get failed: {e}")
            return None
    
    def set_stats(self, stats: Dict, ttl: int = STATS_CACHE_TTL) -> bool:
        """Cache system stats."""
        if not self.enabled:
            return False
        
        try:
            self.client.setex(
                "stats:system",
                ttl,
                json.dumps(stats)
            )
            return True
        except Exception as e:
            logger.warning(f"Stats cache set failed: {e}")
            return False
    
    def invalidate_workspace(self, workspace_id: str) -> int:
        """Invalidate all cache entries for a workspace (e.g., after ingestion)."""
        if not self.enabled:
            return 0
        
        try:
            # Scan for keys matching workspace pattern
            pattern = f"query:*{workspace_id}*"
            keys = list(self.client.scan_iter(match=pattern))
            
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries for workspace {workspace_id}")
                return deleted
            
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
            return 0
    
    def get_metrics(self) -> Dict:
        """Get cache metrics for monitoring."""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            info = self.client.info("stats")
            return {
                "enabled": True,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "keys": self.client.dbsize(),
                "memory_used": info.get("used_memory_human", "unknown")
            }
        except Exception as e:
            logger.warning(f"Failed to get cache metrics: {e}")
            return {"enabled": True, "error": str(e)}
    
    def healthcheck(self) -> bool:
        """Check if Redis is reachable."""
        if not self.enabled:
            return False
        
        try:
            return self.client.ping()
        except Exception:
            return False


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service

