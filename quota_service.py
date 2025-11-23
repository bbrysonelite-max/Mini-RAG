from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Dict, Optional, Tuple

from database import Database

DEFAULT_CHUNK_LIMIT = 500_000
DEFAULT_REQUESTS_PER_DAY = 10_000
DEFAULT_REQUESTS_PER_MINUTE = 120


class QuotaExceededError(Exception):
    """Raised when a workspace exceeds its quota."""

    def __init__(self, message: str, limit: str):
        super().__init__(message)
        self.limit = limit


MetricsHook = Callable[[str, Dict[str, int], Dict[str, int]], None]


class QuotaService:
    """
    Tracks workspace-level usage and enforces chunk/request quotas.
    """

    def __init__(self, db: Database, metrics_hook: Optional[MetricsHook] = None):
        self.db = db
        self._minute_windows: Dict[Tuple[str, datetime], int] = defaultdict(int)
        self._minute_lock = asyncio.Lock()
        self._metrics_hook = metrics_hook
        self._last_minute_usage: Dict[str, int] = defaultdict(int)

    async def consume(
        self,
        workspace_id: str,
        *,
        request_delta: int = 0,
        chunk_delta: int = 0,
        current_chunk_total: Optional[int] = None,
    ) -> None:
        if not workspace_id or (request_delta == 0 and chunk_delta == 0):
            return

        settings = await self._get_settings(workspace_id)
        await self._enforce_limits(
            workspace_id,
            settings,
            request_delta,
            chunk_delta,
            current_chunk_total,
        )
        await self._increment_usage(
            workspace_id,
            request_delta,
            chunk_delta,
            settings,
            current_chunk_total,
        )

    async def _get_settings(self, workspace_id: str) -> Dict[str, int]:
        row = await self.db.fetch_one(
            """
            SELECT chunk_limit, request_limit_per_day, request_limit_per_minute
            FROM workspace_quota_settings
            WHERE workspace_id = $1
            """,
            (workspace_id,),
        )
        if not row:
            return {
                "chunk_limit": DEFAULT_CHUNK_LIMIT,
                "request_limit_per_day": DEFAULT_REQUESTS_PER_DAY,
                "request_limit_per_minute": DEFAULT_REQUESTS_PER_MINUTE,
            }
        return {
            "chunk_limit": row.get("chunk_limit") or DEFAULT_CHUNK_LIMIT,
            "request_limit_per_day": row.get("request_limit_per_day") or DEFAULT_REQUESTS_PER_DAY,
            "request_limit_per_minute": row.get("request_limit_per_minute") or DEFAULT_REQUESTS_PER_MINUTE,
        }

    async def _enforce_limits(
        self,
        workspace_id: str,
        settings: Dict[str, int],
        request_delta: int,
        chunk_delta: int,
        current_chunk_total: Optional[int],
    ) -> None:
        today = date.today()
        usage = await self.db.fetch_one(
            """
            SELECT chunk_count, request_count
            FROM workspace_usage_counters
            WHERE workspace_id = $1 AND bucket_date = $2
            """,
            (workspace_id, today),
        ) or {"chunk_count": 0, "request_count": 0}

        if request_delta:
            projected_requests = usage["request_count"] + request_delta
            if projected_requests > settings["request_limit_per_day"]:
                raise QuotaExceededError("Daily request quota exceeded for workspace.", "requests_per_day")
            await self._enforce_minute_window(workspace_id, settings["request_limit_per_minute"], request_delta)

        if chunk_delta > 0 and current_chunk_total is not None:
            projected_chunks = current_chunk_total + chunk_delta
            if projected_chunks > settings["chunk_limit"]:
                raise QuotaExceededError("Chunk storage quota exceeded for workspace.", "chunk_limit")

    async def _enforce_minute_window(self, workspace_id: str, per_minute_limit: int, request_delta: int) -> None:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        key = (workspace_id, now)
        async with self._minute_lock:
            self._cleanup_minute_windows()
            current = self._minute_windows.get(key, 0)
            if current + request_delta > per_minute_limit:
                raise QuotaExceededError("Per-minute request quota exceeded for workspace.", "requests_per_minute")
            self._minute_windows[key] = current + request_delta
            self._last_minute_usage[workspace_id] = self._minute_windows[key]

    def _cleanup_minute_windows(self) -> None:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        stale_keys = [key for key in self._minute_windows if key[1] < threshold]
        for key in stale_keys:
            self._minute_windows.pop(key, None)

    async def _increment_usage(
        self,
        workspace_id: str,
        request_delta: int,
        chunk_delta: int,
        settings: Dict[str, int],
        current_chunk_total: Optional[int],
    ) -> None:
        today = date.today()
        row = await self.db.fetch_one(
            """
            INSERT INTO workspace_usage_counters (workspace_id, bucket_date, chunk_count, request_count)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (workspace_id, bucket_date)
            DO UPDATE SET
                chunk_count = workspace_usage_counters.chunk_count + EXCLUDED.chunk_count,
                request_count = workspace_usage_counters.request_count + EXCLUDED.request_count
            RETURNING chunk_count, request_count
            """,
            (workspace_id, today, chunk_delta, request_delta),
        )
        usage = row or {"chunk_count": 0, "request_count": 0}
        self._emit_metrics(workspace_id, settings, usage, current_chunk_total, chunk_delta)

    def _emit_metrics(
        self,
        workspace_id: str,
        settings: Dict[str, int],
        usage: Dict[str, int],
        current_chunk_total: Optional[int],
        chunk_delta: int,
    ) -> None:
        if not self._metrics_hook:
            return
        final_chunk_total = None
        if current_chunk_total is not None:
            final_chunk_total = max(current_chunk_total + chunk_delta, 0)
        snapshot = {
            "chunk_count": usage.get("chunk_count", 0),
            "request_count": usage.get("request_count", 0),
            "minute_request_count": self._last_minute_usage.get(workspace_id, 0),
            "current_chunk_total": final_chunk_total,
        }
        enriched_settings = {
            "chunk_limit": settings["chunk_limit"],
            "request_limit_per_day": settings["request_limit_per_day"],
            "request_limit_per_minute": settings["request_limit_per_minute"],
        }
        try:
            self._metrics_hook(workspace_id, enriched_settings, snapshot)
        except Exception:
            # Metrics must not break quota enforcement.
            pass

