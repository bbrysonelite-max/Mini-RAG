import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture
def client():
    return TestClient(server.app)


@pytest.mark.asyncio
async def test_admin_endpoints_require_db(monkeypatch, client):
    async def fake_resolve(request, scopes=("read",), require=True):
        return {"user_id": "admin", "role": "admin"}, None, None

    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)
    server.DB = None

    resp = client.get("/api/v1/admin/workspaces")
    assert resp.status_code == 503

    resp = client.get("/api/v1/admin/billing")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_admin_workspace_listing(monkeypatch, client):
    class FakeDB:
        async def fetch_all(self, query, params=None):
            if "FROM workspaces" in query:
                return [
                    {
                        "id": "ws-1",
                        "name": "Workspace 1",
                        "slug": "workspace-1",
                        "organization_id": "org-1",
                        "organization_name": "Org One",
                        "billing_status": "active",
                        "plan": "pro",
                        "created_at": "2025-01-01",
                        "updated_at": "2025-01-02",
                    }
                ]
            return []

    async def fake_resolve(request, scopes=("read",), require=True):
        return {"user_id": "admin", "role": "admin"}, None, None

    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)
    server.DB = FakeDB()

    resp = client.get("/api/v1/admin/workspaces")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspaces"][0]["organization_name"] == "Org One"


@pytest.mark.asyncio
async def test_admin_billing_patch(monkeypatch, client):
    class FakeDB:
        async def fetch_one(self, query, params=None):
            return {
                "id": "org-1",
                "name": "Org One",
                "plan": "enterprise",
                "billing_status": "active",
            }

    async def fake_resolve(request, scopes=("read",), require=True):
        return {"user_id": "admin", "role": "admin"}, None, None

    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)
    server.DB = FakeDB()

    resp = client.patch("/api/v1/admin/billing/org-1", json={"plan": "enterprise"})
    assert resp.status_code == 200
    assert resp.json()["organization"]["plan"] == "enterprise"

