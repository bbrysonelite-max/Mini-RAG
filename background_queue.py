from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from prometheus_client import Counter, Histogram

JobCallable = Callable[[], Awaitable[Any]]

BACKGROUND_JOBS_SUBMITTED = Counter(
    "background_jobs_submitted_total",
    "Number of background jobs submitted",
    ["name"],
)
BACKGROUND_JOBS_COMPLETED = Counter(
    "background_jobs_completed_total",
    "Number of background jobs completed by outcome",
    ["name", "status"],
)
BACKGROUND_JOB_DURATION = Histogram(
    "background_job_duration_seconds",
    "Duration of background jobs in seconds",
    ["name"],
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)


@dataclass
class BackgroundJob:
    id: str
    name: str
    status: str
    created_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": self.metadata,
            "result": self.result,
            "error": self.error,
        }


class BackgroundTaskQueue:
    """Simple asyncio-backed worker queue for maintenance jobs."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[str, JobCallable]] = asyncio.Queue()
        self._jobs: Dict[str, BackgroundJob] = {}
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    def submit(self, name: str, job_factory: JobCallable, *, metadata: Optional[Dict[str, Any]] = None) -> BackgroundJob:
        job_id = str(uuid.uuid4())
        job = BackgroundJob(
            id=job_id,
            name=name,
            status="queued",
            created_at=time.time(),
            metadata=metadata or {},
        )
        self._jobs[job_id] = job
        BACKGROUND_JOBS_SUBMITTED.labels(name=name).inc()
        self._queue.put_nowait((job_id, job_factory))
        return job

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [job.to_dict() for job in jobs[:limit]]

    async def wait_for_all(self) -> None:
        await self._queue.join()

    async def _worker_loop(self) -> None:
        while True:
            job_id, job_factory = await self._queue.get()
            job = self._jobs.get(job_id)
            if not job:
                self._queue.task_done()
                continue
            job.status = "running"
            job.started_at = time.time()
            start = time.perf_counter()
            try:
                result = await job_factory()
                job.result = result
            except Exception as exc:  # pragma: no cover - error path tested separately
                job.status = "failed"
                job.error = str(exc)
                BACKGROUND_JOBS_COMPLETED.labels(name=job.name, status="failed").inc()
            else:
                job.status = "succeeded"
                BACKGROUND_JOBS_COMPLETED.labels(name=job.name, status="succeeded").inc()
            finally:
                job.finished_at = time.time()
                duration = max(time.perf_counter() - start, 0.0)
                BACKGROUND_JOB_DURATION.labels(name=job.name).observe(duration)
                self._queue.task_done()
