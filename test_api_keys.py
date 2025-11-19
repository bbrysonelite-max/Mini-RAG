"""
Tests for API key generation and management helpers.

These tests rely on Database.execute/execute_many/fetch_* behaviour, so we stub a
minimal async fake that records queries and returns predetermined results.
"""

import asyncio
import pytest

from api_key_service import ApiKeyService, ApiKeyServiceError


class FakeDB:
    def __init__(self):
        self.queries = []
        self.fetch_one_response = None
        self.fetch_all_response = None
        self.execute_response = None

    async def fetch_one(self, query, params=None):
        self.queries.append(("fetch_one", query, params))
        return self.fetch_one_response

    async def fetch_all(self, query, params=None):
        self.queries.append(("fetch_all", query, params))
        return self.fetch_all_response or []

    async def execute(self, query, params=None, fetch=False):
        self.queries.append(("execute", query, params, fetch))
        return self.execute_response


@pytest.mark.asyncio
async def test_create_api_key_success(monkeypatch):
    db = FakeDB()
    db.fetch_one_response = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "workspace_id": None,
        "key_prefix": "abcdefabcdef",
        "scopes": ["read"],
        "description": None,
        "created_at": "2025-11-19T00:00:00Z",
        "last_used_at": None,
        "revoked_at": None,
    }

    # Patch randomness so the test is deterministic.
    monkeypatch.setattr("api_key_service.ApiKeyService._generate_plaintext_key", lambda length_bytes=32: "test-key")
    monkeypatch.setattr("api_key_service.ApiKeyService._derive_prefix", lambda api_key, length=12: "abcdefabcdef")
    monkeypatch.setattr("api_key_service.ApiKeyService._hash_api_key", lambda api_key: "deadbeef" * 8)

    service = ApiKeyService(db)
    result = await service.create_api_key(user_id="22222222-2222-2222-2222-222222222222")

    assert result["api_key"] == "test-key"
    assert result["key_prefix"] == "abcdefabcdef"
    assert "deadbeef" * 8 in db.queries[0][2]  # hashed key stored


@pytest.mark.asyncio
async def test_create_api_key_failure(monkeypatch):
    db = FakeDB()

    async def failing_fetch_one(*args, **kwargs):
        raise Exception("db-error")

    db.fetch_one = failing_fetch_one  # type: ignore[assignment]

    service = ApiKeyService(db)
    with pytest.raises(ApiKeyServiceError):
        await service.create_api_key(user_id="user")


@pytest.mark.asyncio
async def test_list_api_keys_filters():
    db = FakeDB()
    db.fetch_all_response = [
        {"id": "key1", "scopes": ["read"], "revoked_at": None},
        {"id": "key2", "scopes": ["write"], "revoked_at": None},
    ]
    service = ApiKeyService(db)
    rows = await service.list_api_keys(user_id="user-1")

    assert len(rows) == 2
    assert rows[0]["scopes"] == ["read"]
    assert db.queries[0][2][0] == "user-1"


@pytest.mark.asyncio
async def test_revoke_api_key_updates_row():
    db = FakeDB()
    db.fetch_one_response = {"id": "key-123"}
    service = ApiKeyService(db)

    updated = await service.revoke_api_key("key-123")
    assert updated is True
    assert db.queries[-1][0] == "fetch_one"


@pytest.mark.asyncio
async def test_revoke_api_key_handles_failure():
    db = FakeDB()

    async def failing_fetch_one(*args, **kwargs):
        raise Exception("db-failure")

    db.fetch_one = failing_fetch_one  # type: ignore[assignment]
    service = ApiKeyService(db)

    with pytest.raises(ApiKeyServiceError):
        await service.revoke_api_key("key-123")


@pytest.mark.asyncio
async def test_verify_api_key_returns_row(monkeypatch):
    db = FakeDB()
    db.fetch_one_response = {
        "id": "key-123",
        "user_id": "user",
        "workspace_id": None,
        "key_prefix": "abcdefabcdef",
        "hashed_key": "deadbeef" * 8,
        "scopes": ["read", "write"],
        "description": "Test key",
        "created_at": "2025-11-19T00:00:00Z",
        "last_used_at": None,
        "revoked_at": None,
    }

    monkeypatch.setattr("api_key_service.ApiKeyService._derive_prefix", lambda api_key, length=12: "abcdefabcdef")
    monkeypatch.setattr("api_key_service.ApiKeyService._hash_api_key", lambda api_key: "deadbeef" * 8)

    service = ApiKeyService(db)
    row = await service.verify_api_key("test-key")

    assert row is not None
    assert row["scopes"] == ["read", "write"]
    assert db.queries[0][2][0] == "abcdefabcdef"


@pytest.mark.asyncio
async def test_touch_last_used_swallow_errors(monkeypatch):
    db = FakeDB()

    async def failing_execute(*args, **kwargs):
        raise Exception("db failure")

    db.execute = failing_execute  # type: ignore[assignment]
    service = ApiKeyService(db)

    # Should not raise
    await service.touch_last_used("key-123")

