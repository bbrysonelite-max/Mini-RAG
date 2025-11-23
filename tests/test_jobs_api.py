from fastapi.testclient import TestClient

import server


def test_jobs_endpoint_disabled_returns_503():
    with TestClient(server.app) as client:
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 503


def test_jobs_endpoint_lists_jobs(monkeypatch):
    async def fake_resolve(request, scopes=("write",), require=True):
        return {"user_id": "tester"}, None, None

    monkeypatch.setattr(server, "BACKGROUND_JOBS_ENABLED", True)
    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)

    with TestClient(server.app) as client:
        queue = server.BACKGROUND_QUEUE
        assert queue is not None

        async def job():
            return None

        record = queue.submit("demo", job)

        import time

        deadline = time.time() + 1.0
        while time.time() < deadline:
            stored = queue.get_job(record.id)
            if stored and stored.status not in {"queued", "running"}:
                break
            time.sleep(0.01)

        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 200
        body = resp.json()
        assert "jobs" in body
        assert body["jobs"]
        assert body["jobs"][0]["name"] == "demo"
