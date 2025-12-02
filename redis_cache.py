"""
Redis caching layer for Mini-RAG application.

Provides caching for:
- Query results
- Chunk lookups
- Session storage
- Rate limiting backend
"""

import os
import json
import pickle
import hashlib
import logging
from typing import Any, Optional, Dict, List, Union
from datetime import timedelta

logger = logging.getLogger(__name__)

# Check for Redis availability
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis not installed. Run: pip install redis[hiredis]")
    REDIS_AVAILABLE = False
    Redis = None  # type: ignore


class CacheService:
    """
    Redis-backed caching service.
    
    Provides async caching with automatic serialization/deserialization.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "mini_rag"
    ):
        """
        Initialize cache service.
        
        Args:
            redis_url: Redis connection URL (redis://host:port/db)
            default_ttl: Default TTL in seconds
            key_prefix: Prefix for all cache keys
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis client not available")
        
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.client: Optional[Redis] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to Redis."""
        if self._connected:
            return
        
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
                health_check_interval=30,
                socket_keepalive=True,
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
            )
            
            # Test connection
            await self.client.ping()
            self._connected = True
            logger.info(f"Connected to Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
            self._connected = False
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
            self._connected = False
            logger.info("Disconnected from Redis")
    
    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Generate namespaced cache key."""
        parts = [self.key_prefix]
        if namespace:
            parts.append(namespace)
        parts.append(key)
        return ":".join(parts)
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if isinstance(value, (str, bytes)):
            return value.encode() if isinstance(value, str) else value
        elif isinstance(value, (dict, list)):
            return json.dumps(value).encode()
        else:
            # Use pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes, value_type: Optional[str] = None) -> Any:
        """Deserialize value from storage."""
        if not data:
            return None
        
        if value_type == "str":
            return data.decode()
        elif value_type == "json":
            return json.loads(data.decode())
        else:
            # Try JSON first, then pickle
            try:
                return json.loads(data.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                try:
                    return pickle.loads(data)
                except:
                    return data.decode()
    
    async def get(
        self,
        key: str,
        namespace: Optional[str] = None,
        value_type: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            namespace: Optional namespace
            value_type: Hint for deserialization ('str', 'json', or None)
            
        Returns:
            Cached value or None
        """
        if not self._connected or not self.client:
            return None
        
        try:
            full_key = self._make_key(key, namespace)
            data = await self.client.get(full_key)
            
            if data is None:
                return None
            
            return self._deserialize(data, value_type)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
            namespace: Optional namespace
            
        Returns:
            True if successful
        """
        if not self._connected or not self.client:
            return False
        
        try:
            full_key = self._make_key(key, namespace)
            serialized = self._serialize(value)
            ttl = ttl or self.default_ttl
            
            await self.client.set(
                full_key,
                serialized,
                ex=ttl
            )
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False
    
    async def delete(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            namespace: Optional namespace
            
        Returns:
            True if key existed and was deleted
        """
        if not self._connected or not self.client:
            return False
        
        try:
            full_key = self._make_key(key, namespace)
            result = await self.client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False
    
    async def exists(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            namespace: Optional namespace
            
        Returns:
            True if key exists
        """
        if not self._connected or not self.client:
            return False
        
        try:
            full_key = self._make_key(key, namespace)
            return await self.client.exists(full_key) > 0
        except Exception as e:
            logger.warning(f"Cache exists check failed for {key}: {e}")
            return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """
        Clear all keys in a namespace.
        
        Args:
            namespace: Namespace to clear
            
        Returns:
            Number of keys deleted
        """
        if not self._connected or not self.client:
            return 0
        
        try:
            pattern = self._make_key("*", namespace)
            keys = await self.client.keys(pattern)
            
            if not keys:
                return 0
            
            return await self.client.delete(*keys)
        except Exception as e:
            logger.warning(f"Failed to clear namespace {namespace}: {e}")
            return 0
    
    async def get_or_compute(
        self,
        key: str,
        compute_func,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        value_type: Optional[str] = None
    ) -> Any:
        """
        Get value from cache or compute if missing.
        
        Args:
            key: Cache key
            compute_func: Async function to compute value if not cached
            ttl: TTL in seconds
            namespace: Optional namespace
            value_type: Hint for deserialization
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        value = await self.get(key, namespace, value_type)
        if value is not None:
            logger.debug(f"Cache hit for {key}")
            return value
        
        # Compute value
        logger.debug(f"Cache miss for {key}, computing...")
        value = await compute_func()
        
        # Cache the result
        await self.set(key, value, ttl, namespace)
        
        return value
    
    # Query result caching
    async def cache_query_result(
        self,
        query: str,
        result: Dict[str, Any],
        workspace_id: Optional[str] = None,
        ttl: int = 300
    ) -> bool:
        """
        Cache a query result.
        
        Args:
            query: Query string
            result: Query result
            workspace_id: Optional workspace ID
            ttl: TTL in seconds (default 5 minutes)
            
        Returns:
            True if cached successfully
        """
        # Generate cache key from query hash
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        namespace = f"query:{workspace_id}" if workspace_id else "query:global"
        
        return await self.set(query_hash, result, ttl, namespace)
    
    async def get_cached_query_result(
        self,
        query: str,
        workspace_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached query result.
        
        Args:
            query: Query string
            workspace_id: Optional workspace ID
            
        Returns:
            Cached result or None
        """
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        namespace = f"query:{workspace_id}" if workspace_id else "query:global"
        
        return await self.get(query_hash, namespace, "json")
    
    # Session storage
    async def set_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: int = 86400
    ) -> bool:
        """
        Store session data.
        
        Args:
            session_id: Session ID
            data: Session data
            ttl: TTL in seconds (default 24 hours)
            
        Returns:
            True if stored successfully
        """
        return await self.set(session_id, data, ttl, "session")
    
    async def get_session(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None
        """
        return await self.get(session_id, "session", "json")
    
    # Rate limiting
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check and update rate limit.
        
        Args:
            identifier: User/IP identifier
            limit: Max requests in window
            window: Time window in seconds
            
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        if not self._connected or not self.client:
            # Allow if cache not available
            return True, limit
        
        try:
            key = self._make_key(identifier, "ratelimit")
            
            # Use Redis pipeline for atomic operation
            async with self.client.pipeline() as pipe:
                pipe.incr(key)
                pipe.expire(key, window)
                results = await pipe.execute()
            
            count = results[0]
            allowed = count <= limit
            remaining = max(0, limit - count)
            
            return allowed, remaining
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True, limit
    
    # Cache statistics
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        if not self._connected or not self.client:
            return {"connected": False}
        
        try:
            info = await self.client.info("stats")
            memory = await self.client.info("memory")
            
            return {
                "connected": True,
                "total_connections": info.get("total_connections_received", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "used_memory": memory.get("used_memory_human", "unknown"),
                "peak_memory": memory.get("used_memory_peak_human", "unknown"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) /
                    max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                ) * 100
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"connected": False, "error": str(e)}


# Global cache instance
_global_cache: Optional[CacheService] = None


def get_cache_service(redis_url: Optional[str] = None) -> Optional[CacheService]:
    """
    Get the global cache service instance.
    
    Args:
        redis_url: Optional Redis URL (only used on first call)
        
    Returns:
        CacheService instance or None if not available
    """
    global _global_cache
    
    if not REDIS_AVAILABLE:
        return None
    
    if _global_cache is None:
        try:
            _global_cache = CacheService(redis_url)
        except Exception as e:
            logger.warning(f"Failed to initialize cache service: {e}")
            return None
    
    return _global_cache


async def init_cache_service(redis_url: Optional[str] = None) -> Optional[CacheService]:
    """
    Initialize the global cache service.
    
    Args:
        redis_url: Optional Redis URL
        
    Returns:
        Initialized CacheService or None if not available
    """
    cache = get_cache_service(redis_url)
    
    if cache and not cache._connected:
        try:
            await cache.connect()
        except Exception as e:
            logger.warning(f"Failed to connect to cache: {e}")
            return None
    
    return cache
