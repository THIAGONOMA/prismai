"""Router for full-text eligibility assessment (F6)."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.jobs import create_job, get_job, publish_event
from prismai.api.schemas import EligibilityDecisionResponse, JobResponse, RunEligibilityRequest
from prismai.graphs.eligibility import evaluate_eligibility
from prismai.llm.client import criar_llm
from prismai.persistence.repository import ReviewRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/reviews", tags=["eligibility"])


@router.post("/{review_id}/eligibility/run", response_model=JobResponse, status_code=202)
async def run_eligibility(
    review_id: str,
    body: RunEligibilityRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")
    protocol = await repo.get_protocol(review_id)
    if not protocol:
        raise HTTPException(400, "Protocol not set")

    docs = await repo.get_documents(review_id, status="extracted")
    if not docs:
        raise HTTPException(400, "No extracted documents to evaluate")

    job = create_job(review_id, total=len(docs))
    llm = criar_llm(model=body.model, temperature=body.temperature)

    async def _bg():
        records = await repo.get_records(review_id)
        records_by_id = {r["id"]: r for r in records}

        for i, doc in enumerate(docs):
            record_id = doc.get("record_id", "")
            record = records_by_id.get(record_id, {"id": record_id})

            try:
                resposta, metricas = await asyncio.to_thread(
                    evaluate_eligibility, doc, record, protocol, llm
                )
            except Exception as e:
                logger.error("Eligibility failed for %s: %s", record_id, e)
                continue

            elig_data = {
                "record_id": record_id,
                "decision": resposta.resultado.decision,
                "exclusion_reason": resposta.resultado.exclusion_reason,
                "confidence": resposta.resultado.confidence,
                "reasons": [cr.reasoning for cr in resposta.resultado.criteria_results],
                "degradado": resposta.degradado,
                "alertas": resposta.alertas,
            }
            await repo.add_eligibility_decision(review_id, elig_data)

            for cr in resposta.resultado.criteria_results:
                for span in cr.evidence_spans:
                    await repo.add_evidence_span(review_id, {
                        "record_id": record_id,
                        "page": span.page,
                        "start": span.start,
                        "end": span.end,
                        "text": span.text,
                        "criterion": cr.criterion,
                    })

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


@router.get("/{review_id}/eligibility", response_model=list[EligibilityDecisionResponse])
async def list_eligibility_decisions(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    decisions = await repo.get_eligibility_decisions(review_id)
    return [EligibilityDecisionResponse(**d) for d in decisions]
