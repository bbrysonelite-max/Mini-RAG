"""
Request deduplication to prevent duplicate concurrent expensive operations.
When multiple clients ask the same question simultaneously, only execute once.
"""

import asyncio
import logging
import hashlib
import json
from typing import Any, Dict, Optional, Callable, TypeVar, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger("rag")

T = TypeVar("T")


@dataclass
class PendingRequest:
    """Tracks an in-flight request."""
    future: asyncio.Future
    created_at: datetime = field(default_factory=datetime.utcnow)
    waiters: int = 0


class RequestDeduplicator:
    """
    Deduplicates concurrent requests by key.
    
    When multiple identical requests arrive simultaneously:
    - First request executes normally
    - Subsequent requests wait for first to complete
    - All requests receive the same result
    """
    
    def __init__(self, ttl_seconds: int = 30):
        self._pending: Dict[str, PendingRequest] = {}
        self._lock = asyncio.Lock()
        self.ttl_seconds = ttl_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start_cleanup(self):
        """Start background task to clean up stale entries."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Periodically remove stale entries."""
        while True:
            try:
                await asyncio.sleep(self.ttl_seconds)
                await self._cleanup_stale()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dedup cleanup error: {e}")
    
    async def _cleanup_stale(self):
        """Remove entries older than TTL."""
        async with self._lock:
            now = datetime.utcnow()
            stale_keys = [
                key for key, req in self._pending.items()
                if (now - req.created_at).total_seconds() > self.ttl_seconds
            ]
            
            for key in stale_keys:
                req = self._pending.pop(key, None)
                if req and not req.future.done():
                    req.future.cancel()
            
            if stale_keys:
                logger.debug(f"Cleaned up {len(stale_keys)} stale dedup entries")
    
    def _make_key(self, request_data: Dict[str, Any]) -> str:
        """Generate a stable key from request parameters."""
        serialized = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
    
    async def deduplicate(
        self,
        key_data: Dict[str, Any],
        executor: Callable[[], Awaitable[T]]
    ) -> T:
        """
        Execute a function, deduplicating concurrent identical requests.
        
        Args:
            key_data: Dictionary representing the request (query, params, workspace, etc.)
            executor: Async function to execute if this is the first request
        
        Returns:
            Result from executor (either fresh or from deduplicated request)
        """
        key = self._make_key(key_data)
        
        async with self._lock:
            if key in self._pending:
                # Request already in flight - wait for it
                pending = self._pending[key]
                pending.waiters += 1
                logger.info(f"Deduplicating request {key} ({pending.waiters} waiters)")
        
        # If we found a pending request, wait outside the lock
        if key in self._pending:
            try:
                result = await self._pending[key].future
                logger.debug(f"Dedup hit: {key}")
                return result
            except Exception as e:
                # If the original request failed, raise the same error
                logger.debug(f"Dedup failed (original failed): {key}")
                raise
        
        # This is the first request - execute it
        async with self._lock:
            # Double-check in case another task beat us
            if key in self._pending:
                pending = self._pending[key]
                pending.waiters += 1
        
        if key in self._pending:
            try:
                return await self._pending[key].future
            except Exception:
                raise
        
        # We're the first - create a future and execute
        future = asyncio.Future()
        async with self._lock:
            self._pending[key] = PendingRequest(future=future)
        
        try:
            logger.debug(f"Executing request {key} (first)")
            result = await executor()
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            # Clean up after completion
            async with self._lock:
                self._pending.pop(key, None)
    
    def get_stats(self) -> Dict[str, int]:
        """Get deduplication statistics."""
        total_waiters = sum(req.waiters for req in self._pending.values())
        return {
            "pending_requests": len(self._pending),
            "total_waiters": total_waiters,
            "dedup_savings": total_waiters  # Number of executions saved
        }
    
    async def shutdown(self):
        """Gracefully shut down the deduplicator."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel any remaining futures
        async with self._lock:
            for req in self._pending.values():
                if not req.future.done():
                    req.future.cancel()
            self._pending.clear()


# Global singleton
_deduplicator: Optional[RequestDeduplicator] = None


def get_deduplicator() -> RequestDeduplicator:
    """Get the global request deduplicator."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = RequestDeduplicator()
        _deduplicator.start_cleanup()
    return _deduplicator

