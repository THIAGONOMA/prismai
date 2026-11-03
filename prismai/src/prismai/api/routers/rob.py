"""Router for Risk of Bias assessment (F8)."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.jobs import create_job, get_job, publish_event
from prismai.api.schemas import JobResponse, RobAssessmentResponse, RunRobRequest
from prismai.graphs.rob import assess_rob
from prismai.llm.client import criar_llm
from prismai.persistence.repository import ReviewRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/reviews", tags=["rob"])


@router.post("/{review_id}/rob/run", response_model=JobResponse, status_code=202)
async def run_rob(
    review_id: str,
    body: RunRobRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")

    extractions = await repo.get_extractions(review_id)
    extracted_ids = {e["record_id"] for e in extractions if e.get("status") == "completed"}

    existing_rob = await repo.get_rob_assessments(review_id)
    assessed_ids = {r["record_id"] for r in existing_rob}
    pending_ids = extracted_ids - assessed_ids

    docs = await repo.get_documents(review_id, status="extracted")
    pending_docs = [d for d in docs if d.get("record_id") in pending_ids]
    if not pending_docs:
        raise HTTPException(400, "No pending documents for RoB assessment")

    job = create_job(review_id, total=len(pending_docs))
    llm = criar_llm(model=body.model, temperature=body.temperature)

    async def _bg():
        records = await repo.get_records(review_id)
        records_by_id = {r["id"]: r for r in records}

        for i, doc in enumerate(pending_docs):
            record_id = doc.get("record_id", "")
            record = records_by_id.get(record_id, {"id": record_id})

            try:
                resposta, metricas = await asyncio.to_thread(
                    assess_rob, doc, record, llm,
                )
            except Exception as e:
                logger.error("RoB failed for %s: %s", record_id, e)
                continue

            rob_data = {
                "record_id": record_id,
                "instrument": resposta.resultado.instrument,
                "overall_judgment": resposta.resultado.overall,
                "domain_results": [d.model_dump() for d in resposta.resultado.domains],
                "degradado": resposta.degradado,
                "alertas": resposta.alertas,
            }
            await repo.add_rob_assessment(review_id, rob_data)
            await repo.add_trace(review_id, metricas)

            j = get_job(job.id)
            if j:
                j.progress = i + 1
            publish_event(job.id, {"type": "progress", "progress": i + 1})

        j = get_job(job.id)
        if j:
            j.status = "completed"
        publish_event(job.id, {"type": "done"})

    asyncio.get_event_loop().create_task(_bg())
    return JobResponse(job_id=job.id, status=job.status, progress=0, total=job.total)


@router.get("/{review_id}/rob", response_model=list[RobAssessmentResponse])
async def list_rob_assessments(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    assessments = await repo.get_rob_assessments(review_id)
    return [RobAssessmentResponse(**a) for a in assessments]
