"""Job tracking with dual backends: in-memory (dev/test) and Postgres (production).

In-memory backend uses asyncio.Queue for SSE; Postgres backend uses pg_notify/LISTEN.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Job:
    id: str
    review_id: str
    status: str = "pending"
    progress: int = 0
    total: int = 0
    created_at: str = ""
    events: list[dict] = field(default_factory=list)
    result: Any = None
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# In-memory backend (used by dev/test without Postgres)
# ---------------------------------------------------------------------------
_jobs: dict[str, Job] = {}
_event_queues: dict[str, list[asyncio.Queue]] = {}


def create_job(review_id: str, total: int) -> Job:
    job = Job(id=str(uuid.uuid4()), review_id=review_id, status="running", total=total)
    _jobs[job.id] = job
    _event_queues[job.id] = []
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def publish_event(job_id: str, event: dict) -> None:
    job = _jobs.get(job_id)
    enriched = {**event, "job_id": job_id}
    if job:
        enriched.setdefault("progress", job.progress)
        enriched.setdefault("total", job.total)
        job.events.append(enriched)
    for q in _event_queues.get(job_id, []):
        q.put_nowait(enriched)


def subscribe(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _event_queues.setdefault(job_id, []).append(q)
    return q


def unsubscribe(job_id: str, q: asyncio.Queue) -> None:
    qs = _event_queues.get(job_id, [])
    if q in qs:
        qs.remove(q)


def reset_jobs() -> None:
    _jobs.clear()
    _event_queues.clear()


# ---------------------------------------------------------------------------
# Postgres backend: pg_notify listener for SSE
# ---------------------------------------------------------------------------

async def listen_pg_events(job_id: str, database_url: str):
    """Async generator yielding SSE-formatted events from pg_notify.

    Falls back gracefully if psycopg is not available or connection fails.
    """
    try:
        import psycopg

        conn = await psycopg.AsyncConnection.connect(
            database_url.replace("+psycopg", "").replace("postgresql", "postgresql"),
            autocommit=True,
        )
    except Exception:
        return

    try:
        await conn.execute("LISTEN job_events")
        while True:
            try:
                gen = conn.notifies(timeout=30.0)
                async for notify in gen:
                    try:
                        payload = json.loads(notify.payload)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if payload.get("job_id") != job_id:
                        continue
                    yield f"data: {json.dumps(payload)}\n\n"
                    if payload.get("type") == "done":
                        return
                # timeout reached, send ping
                yield "event: ping\ndata: {}\n\n"
            except asyncio.TimeoutError:
                yield "event: ping\ndata: {}\n\n"
    finally:
        await conn.close()
