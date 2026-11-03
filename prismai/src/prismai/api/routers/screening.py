from __future__ import annotations

import asyncio
import logging
from typing import Any

import anyio
from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.jobs import create_job, publish_event
from prismai.api.schemas import JobResponse, RunScreeningRequest
from prismai.graphs.screening import screen_v4
from prismai.llm.client import criar_llm
from prismai.persistence.repository import ReviewRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/reviews", tags=["screening"])


def _run_screening_sync(
    records: list[dict],
    protocol: dict,
    llm: Any,
    review_id: str,
    job_id: str,
    repo: ReviewRepository,
) -> None:
    """In-memory fallback: runs screening in a thread within the API process."""
    import asyncio as _aio

    from prismai.api.jobs import get_job

    loop = _aio.new_event_loop()
    job = get_job(job_id)
    try:
        for i, rec in enumerate(records):
            resposta, metricas = screen_v4(rec, protocol, llm)
            decision_data = {
                "registro_id": rec["id"],
                "decision": resposta.resultado.decision,
                "confidence": resposta.resultado.confidence,
                "reasons": resposta.resultado.reasons,
                "evidence": resposta.resultado.evidence,
                "degradado": resposta.degradado,
                "alertas": resposta.alertas,
            }
            loop.run_until_complete(repo.add_decision(review_id, decision_data))
            loop.run_until_complete(repo.add_trace(review_id, metricas))
            if job:
                job.progress = i + 1
            publish_event(job_id, {"type": "progress", "registro_id": rec["id"], "progress": i + 1})

        if job:
            job.status = "completed"
        publish_event(job_id, {"type": "done"})
    finally:
        loop.close()


@router.post("/{review_id}/screening/run", response_model=JobResponse, status_code=202)
async def run_screening(
    review_id: str,
    body: RunScreeningRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")
    protocol = await repo.get_protocol(review_id)
    if not protocol:
        raise HTTPException(400, "Protocol not set")
    records = await repo.get_records(review_id)
    if not records:
        raise HTTPException(400, "No records to screen")

    llm = criar_llm(model=body.model, temperature=body.temperature)
    job = create_job(review_id, total=len(records))

    # In-memory fallback (no SAQ queue available in test/dev without Postgres)
    async def _bg():
        await anyio.to_thread.run_sync(
            lambda: _run_screening_sync(records, protocol, llm, review_id, job.id, repo)
        )

    asyncio.get_event_loop().create_task(_bg())
    return JobResponse(job_id=job.id, status=job.status, progress=0, total=job.total)
