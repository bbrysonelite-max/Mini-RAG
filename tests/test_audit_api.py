import uuid

from fastapi.testclient import TestClient

import server


def test_audit_endpoint_requires_admin(monkeypatch):
    async def fake_resolve(request, scopes=("admin",), require=True):
        return None, None, None

    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)

    with TestClient(server.app) as client:
        resp = client.get("/api/v1/admin/audit")
        assert resp.status_code in {401, 403}


def test_audit_endpoint_returns_events(monkeypatch):
    marker = str(uuid.uuid4())
    server._log_event("test.audit", marker=marker)

    async def fake_resolve(request, scopes=("admin",), require=True):
        return {"role": "admin", "user_id": "tester"}, None, None

    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)

    with TestClient(server.app) as client:
        resp = client.get("/api/v1/admin/audit?limit=200")
        assert resp.status_code == 200
        body = resp.json()
        events = body.get("events", [])
        assert any(event.get("event") == "test.audit" and event.get("marker") == marker for event in events)
