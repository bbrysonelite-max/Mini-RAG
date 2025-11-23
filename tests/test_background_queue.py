import asyncio

import pytest

from background_queue import BackgroundTaskQueue


@pytest.mark.asyncio
async def test_background_queue_executes_job_successfully():
    queue = BackgroundTaskQueue()
    await queue.start()
    called = asyncio.Event()

    async def job():
        called.set()
        return True

    record = queue.submit("demo", job)
    await asyncio.wait_for(called.wait(), timeout=1)
    await asyncio.wait_for(queue.wait_for_all(), timeout=1)
    stored = queue.get_job(record.id)
    assert stored is not None
    assert stored.status == "succeeded"
    assert stored.result is True
    await queue.stop()


@pytest.mark.asyncio
async def test_background_queue_records_failures():
    queue = BackgroundTaskQueue()
    await queue.start()

    async def job():
        raise RuntimeError("boom")

    record = queue.submit("demo", job)
    await asyncio.wait_for(queue.wait_for_all(), timeout=1)
    stored = queue.get_job(record.id)
    assert stored is not None
    assert stored.status == "failed"
    assert stored.error == "boom"
    assert stored.result is None
    await queue.stop()
