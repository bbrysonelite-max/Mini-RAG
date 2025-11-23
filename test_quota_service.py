import asyncio
from datetime import date, datetime, timezone, timedelta

import pytest

import quota_service
from quota_service import QuotaService, QuotaExceededError


class FakeDB:
    def __init__(self):
        self.settings = {}
        self.usage = {}

    async def fetch_one(self, query: str, params):
        if "INSERT INTO workspace_usage_counters" in query:
            workspace_id, bucket_date, chunk_delta, request_delta = params
            key = (workspace_id, bucket_date)
            entry = self.usage.setdefault(key, {"chunk_count": 0, "request_count": 0})
            entry["chunk_count"] += chunk_delta
            entry["request_count"] += request_delta
            return {"chunk_count": entry["chunk_count"], "request_count": entry["request_count"]}
        if "workspace_quota_settings" in query:
            return self.settings.get(params[0])
        if "workspace_usage_counters" in query:
            return self.usage.get((params[0], params[1]))
        return None

    async def execute(self, query: str, params):
        if "workspace_usage_counters" in query:
            workspace_id, bucket_date, chunk_delta, request_delta = params
            key = (workspace_id, bucket_date)
            entry = self.usage.setdefault(key, {"chunk_count": 0, "request_count": 0})
            entry["chunk_count"] += chunk_delta
            entry["request_count"] += request_delta


@pytest.mark.asyncio
async def test_consume_updates_usage_with_defaults():
    db = FakeDB()
    service = QuotaService(db)  # uses default limits
    workspace_id = "ws-default"

    await service.consume(workspace_id, request_delta=5, chunk_delta=10, current_chunk_total=0)

    usage = db.usage.get((workspace_id, date.today()))
    assert usage is not None
    assert usage["request_count"] == 5
    assert usage["chunk_count"] == 10


@pytest.mark.asyncio
async def test_chunk_limit_enforced():
    db = FakeDB()
    workspace_id = "ws-chunks"
    db.settings[workspace_id] = {
        "chunk_limit": 100,
        "request_limit_per_day": 1000,
        "request_limit_per_minute": 100,
    }
    service = QuotaService(db)

    # Within limit
    await service.consume(workspace_id, chunk_delta=90, current_chunk_total=0)

    with pytest.raises(QuotaExceededError):
        await service.consume(workspace_id, chunk_delta=20, current_chunk_total=90)


@pytest.mark.asyncio
async def test_daily_request_limit_enforced():
    db = FakeDB()
    workspace_id = "ws-requests"
    db.settings[workspace_id] = {
        "chunk_limit": 1000,
        "request_limit_per_day": 5,
        "request_limit_per_minute": 5,
    }
    service = QuotaService(db)

    await service.consume(workspace_id, request_delta=5)
    with pytest.raises(QuotaExceededError):
        await service.consume(workspace_id, request_delta=1)


@pytest.mark.asyncio
async def test_per_minute_limit_enforced(monkeypatch):
    db = FakeDB()
    workspace_id = "ws-minute"
    db.settings[workspace_id] = {
        "chunk_limit": 1000,
        "request_limit_per_day": 100,
        "request_limit_per_minute": 2,
    }
    service = QuotaService(db)

    class FrozenDateTime:
        current = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            if tz:
                return cls.current.astimezone(tz)
            return cls.current

    monkeypatch.setattr(quota_service, "datetime", FrozenDateTime)

    await service.consume(workspace_id, request_delta=2)
    with pytest.raises(QuotaExceededError):
        await service.consume(workspace_id, request_delta=1)

    # Advance one minute and ensure window resets
    FrozenDateTime.current += timedelta(minutes=1)
    await service.consume(workspace_id, request_delta=2)


@pytest.mark.asyncio
async def test_metrics_hook_receives_usage():
    db = FakeDB()
    captured = []

    def hook(workspace_id, settings, snapshot):
        captured.append((workspace_id, settings, snapshot))

    service = QuotaService(db, metrics_hook=hook)
    workspace_id = "ws-metrics"

    await service.consume(workspace_id, request_delta=3, chunk_delta=4, current_chunk_total=50)

    assert captured, "metrics hook should be invoked"
    workspace, settings, snapshot = captured[-1]
    assert workspace == workspace_id
    assert snapshot["request_count"] == 3
    assert snapshot["chunk_count"] == 4
    assert snapshot["minute_request_count"] >= 0

