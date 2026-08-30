"""
Minimal in-memory job store backing the async document-analysis flow
(routes/analysis_job_routes.py).

Deliberately not a database or task queue - this is a single-process
FastAPI app, and a dict + per-job asyncio.Queue subscribers is enough to
support REST polling, SSE push, and reconnect-and-poll fallback. If this
ever needs to survive a process restart or run across multiple workers,
that's the point to swap this module out for something persistent -
nothing in the routes layer would need to change.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from models.job_status_model import JobStatus


@dataclass
class Job:
    doc_id: str
    original_file_name: str
    status: JobStatus = JobStatus.QUEUED
    error: Optional[str] = None
    results: Optional[list] = None
    created_at: float = field(default_factory=time.time)
    subscribers: list = field(default_factory=list)  # list[asyncio.Queue]


_jobs: dict[str, Job] = {}


def create_job(doc_id: str, original_file_name: str) -> Job:
    job = Job(doc_id=doc_id, original_file_name=original_file_name)
    _jobs[doc_id] = job
    return job


def get_job(doc_id: str) -> Optional[Job]:
    return _jobs.get(doc_id)


def _publish(job: Job) -> None:
    for queue in job.subscribers:
        queue.put_nowait(job.status)


def set_status(doc_id: str, status: JobStatus) -> None:
    job = _jobs.get(doc_id)
    if job is None:
        return
    job.status = status
    _publish(job)


def set_done(doc_id: str, results: list) -> None:
    job = _jobs.get(doc_id)
    if job is None:
        return
    job.results = results
    job.status = JobStatus.DONE
    _publish(job)


def set_failed(doc_id: str, error: str) -> None:
    job = _jobs.get(doc_id)
    if job is None:
        return
    job.error = error
    job.status = JobStatus.FAILED
    _publish(job)


def subscribe(doc_id: str) -> Optional[asyncio.Queue]:
    job = _jobs.get(doc_id)
    if job is None:
        return None
    queue: asyncio.Queue = asyncio.Queue()
    job.subscribers.append(queue)
    return queue


def unsubscribe(doc_id: str, queue: asyncio.Queue) -> None:
    job = _jobs.get(doc_id)
    if job is None:
        return
    if queue in job.subscribers:
        job.subscribers.remove(queue)
