from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import server


class FakeDB:
    def __init__(self, row):
        self.row = row

    async def fetch_one(self, query, params):
        return self.row


@pytest.fixture(autouse=True)
def reset_db():
    original = server.DB
    yield
    server.DB = original


@pytest.mark.asyncio
async def test_require_billing_active_allows_trial():
    future = datetime.now(timezone.utc) + timedelta(days=2)
    server.DB = FakeDB(
        {
            "billing_status": "trialing",
            "trial_ends_at": future,
            "subscription_expires_at": None,
        }
    )
    await server._require_billing_active("ws-1")


@pytest.mark.asyncio
async def test_require_billing_active_rejects_expired_trial():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    server.DB = FakeDB(
        {
            "billing_status": "trialing",
            "trial_ends_at": past,
            "subscription_expires_at": None,
        }
    )
    with pytest.raises(HTTPException) as exc:
        await server._require_billing_active("ws-1")
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_require_billing_active_rejects_past_due():
    server.DB = FakeDB(
        {
            "billing_status": "past_due",
            "trial_ends_at": None,
            "subscription_expires_at": None,
        }
    )
    with pytest.raises(HTTPException) as exc:
        await server._require_billing_active("ws-1")
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_require_billing_active_rejects_expired_subscription():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    server.DB = FakeDB(
        {
            "billing_status": "active",
            "trial_ends_at": None,
            "subscription_expires_at": past,
        }
    )
    with pytest.raises(HTTPException) as exc:
        await server._require_billing_active("ws-1")
    assert exc.value.status_code == 402

