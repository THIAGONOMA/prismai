from __future__ import annotations

import asyncio
import json
import os

from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse

from prismai.api.jobs import get_job, listen_pg_events, subscribe, unsubscribe
from prismai.api.schemas import JobResponse

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


def _use_pg_events() -> bool:
    return "postgresql" in os.getenv("PRISMAI_DATABASE_URL", "")


@router.get("/{job_id}", response_model=JobResponse)
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobResponse(job_id=job.id, status=job.status, progress=job.progress, total=job.total)


@router.get("/{job_id}/events")
async def job_events(job_id: str):
    """SSE endpoint. Uses pg_notify when Postgres is configured, in-memory Queue otherwise."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if _use_pg_events():
        from prismai.config import settings
        pg_url = settings.database_url

        async def pg_stream():
            async for chunk in listen_pg_events(job_id, pg_url):
                yield chunk

        return StreamingResponse(pg_stream(), media_type="text/event-stream")

    q = subscribe(job_id)

    async def event_stream():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
                    continue
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    break
        finally:
            unsubscribe(job_id, q)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
