from fastapi.testclient import TestClient

import server


def test_jobs_endpoint_disabled_returns_503():
    with TestClient(server.app) as client:
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 503


def test_jobs_endpoint_lists_jobs(monkeypatch):
    class DummyQueue:
        def list_jobs(self, limit=50):
            return [
                {"id": "1", "name": "dedupe", "status": "succeeded", "created_at": 0.0},
            ]

    async def fake_resolve(request, scopes=("write",), require=True):
        return {"user_id": "tester"}, None, None

    monkeypatch.setattr(server, "BACKGROUND_JOBS_ENABLED", True)
    monkeypatch.setattr(server, "BACKGROUND_QUEUE", DummyQueue())
    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)

    with TestClient(server.app) as client:
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 200
        body = resp.json()
        assert "jobs" in body
        assert body["jobs"][0]["name"] == "dedupe"
