import asyncio
from fastapi.testclient import TestClient

import server
from background_queue import BackgroundTaskQueue


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
            return {"ok": True}

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
        assert body["jobs"][0]["result"] == {"ok": True}


def test_ingest_urls_queued(monkeypatch):
    async def fake_resolve(request, scopes=("write",), require=True):
        return {"user_id": "tester"}, "workspace-1", None

    async def fake_billing(workspace_id):
        return None

    async def fake_ingest_core(user, workspace_id, api_key_principal, url_req, urls_list):
        return {"results": [{"url": urls_list[0], "written": 1}], "total_written": 1, "count": 5}

    monkeypatch.setattr(server, "BACKGROUND_JOBS_ENABLED", True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server.BACKGROUND_QUEUE = BackgroundTaskQueue()
    loop.run_until_complete(server.BACKGROUND_QUEUE.start())
    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)
    monkeypatch.setattr(server, "_require_billing_active", fake_billing)
    monkeypatch.setattr(server, "_ingest_urls_core", fake_ingest_core)

    try:
        with TestClient(server.app) as client:
            resp = client.post(
                "/api/ingest_urls",
                data={"urls": "https://youtu.be/demo", "language": "en"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["queued"] is True
            job_id = data["job_id"]

            queue = server.BACKGROUND_QUEUE
            assert queue is not None

            loop.run_until_complete(queue.wait_for_all())
            job = queue.get_job(job_id)
            assert job is not None
            assert job.status == "succeeded"
            assert job.result["total_written"] == 1
    finally:
        if server.BACKGROUND_QUEUE:
            loop.run_until_complete(server.BACKGROUND_QUEUE.stop())
            server.BACKGROUND_QUEUE = None
        loop.close()
        asyncio.set_event_loop(None)


def test_ingest_files_queued(monkeypatch, tmp_path):
    async def fake_resolve(request, scopes=("write",), require=True):
        return {"user_id": "tester"}, "workspace-1", None

    async def fake_billing(workspace_id):
        return None

    async def fake_ingest_files_core(user, workspace_id, api_key_principal, prepared, language, initial_results=None):
        return {"results": [{"file": "doc.txt", "written": 2}], "total_written": 2, "count": 10}

    monkeypatch.setattr(server, "BACKGROUND_JOBS_ENABLED", True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server.BACKGROUND_QUEUE = BackgroundTaskQueue()
    loop.run_until_complete(server.BACKGROUND_QUEUE.start())
    monkeypatch.setattr(server, "_resolve_auth_context", fake_resolve)
    monkeypatch.setattr(server, "_require_billing_active", fake_billing)
    monkeypatch.setattr(server, "_ingest_files_core", fake_ingest_files_core)

    from io import BytesIO
    from starlette.datastructures import UploadFile

    upload = UploadFile(filename="doc.txt", file=BytesIO(b"hello"))

    try:
        with TestClient(server.app) as client:
            resp = client.post(
                "/api/ingest_files",
                data={"language": "en"},
                files={"files": ("doc.txt", b"hello", "text/plain")},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["queued"] is True
            job_id = data["job_id"]

            queue = server.BACKGROUND_QUEUE
            assert queue is not None

            loop.run_until_complete(queue.wait_for_all())
            job = queue.get_job(job_id)
            assert job is not None
            assert job.status == "succeeded"
            assert job.result["total_written"] == 2
    finally:
        if server.BACKGROUND_QUEUE:
            loop.run_until_complete(server.BACKGROUND_QUEUE.stop())
            server.BACKGROUND_QUEUE = None
        loop.close()
        asyncio.set_event_loop(None)
