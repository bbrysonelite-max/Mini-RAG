import asyncio

from fastapi.testclient import TestClient

import server
from background_queue import BackgroundTaskQueue


def test_metrics_endpoint_exposes_core_metrics(monkeypatch):
    # Seed key metrics with sample data so they appear in scrape output.
    server.ASK_REQUEST_COUNTER.labels(outcome="success", status_code="200").inc()
    server.ASK_LATENCY.labels(outcome="success").observe(0.2)
    server.INGEST_COUNTER.labels(source="youtube", outcome="success", status_code="200").inc()
    server.INGEST_LATENCY.labels(source="youtube", outcome="success").observe(0.4)
    server.INGEST_PROCESSED_CHUNKS.labels(source="youtube").inc(3)
    server.WORKSPACE_QUOTA_USAGE.labels("workspace-test", "requests_today").set(42)
    server.WORKSPACE_QUOTA_RATIO.labels("workspace-test", "requests_per_day").set(0.5)
    server.QUOTA_EXCEEDED_COUNTER.labels("workspace-test", "requests_per_day").inc()
    server.EXTERNAL_REQUEST_ERRORS.labels("stripe", "checkout").inc()

    # Exercise background job metrics by running a short-lived job.
    monkeypatch.setattr(server, "BACKGROUND_JOBS_ENABLED", True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    queue = BackgroundTaskQueue()
    loop.run_until_complete(queue.start())
    server.BACKGROUND_QUEUE = queue

    async def job():
        return "ok"

    record = queue.submit("metrics_test", job)
    loop.run_until_complete(queue.wait_for_all())

    try:
        with TestClient(server.app) as client:
            resp = client.get("/metrics")
            assert resp.status_code == 200
            body = resp.text

        expected_snippets = [
            'ask_requests_total{outcome="success",status_code="200"}',
            'ask_request_latency_seconds_bucket{le="0.5",outcome="success"}',
            'ingest_operations_total{outcome="success",source="youtube",status_code="200"}',
            'ingest_processed_chunks_total{source="youtube"}',
            'workspace_quota_ratio{metric="requests_per_day",workspace_id="workspace-test"}',
            'quota_exceeded_total{metric="requests_per_day",workspace_id="workspace-test"}',
            'external_request_errors_total{operation="checkout",service="stripe"}',
            f'background_jobs_submitted_total{{name="{record.name}"}}',
            f'background_jobs_completed_total{{name="{record.name}",status="succeeded"}}',
            'background_job_duration_seconds_bucket{le="0.5",name="metrics_test"}',
        ]

        for snippet in expected_snippets:
            assert snippet in body
    finally:
        loop.run_until_complete(queue.stop())
        server.BACKGROUND_QUEUE = None
        asyncio.set_event_loop(None)
        loop.close()
