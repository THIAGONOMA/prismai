"""Router for GRADE certainty-of-evidence assessment (M6)."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.jobs import create_job, get_job, publish_event
from prismai.api.schemas import (
    GradeAssessmentResponse,
    GradeDomainResponse,
    JobResponse,
    RunGradeRequest,
    SofEntry,
    SofResponse,
)
from prismai.graphs.grade import assess_grade
from prismai.llm.client import criar_llm
from prismai.persistence.repository import ReviewRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/reviews", tags=["grade"])


@router.post("/{review_id}/grade/run", response_model=JobResponse, status_code=202)
async def run_grade(
    review_id: str,
    body: RunGradeRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")

    syntheses = await repo.get_syntheses(review_id)
    if not syntheses:
        raise HTTPException(400, "No syntheses available for GRADE assessment")

    existing = await repo.get_grade_assessments(review_id)
    graded_keys = {g["outcome_key"] for g in existing}
    pending = [s for s in syntheses if s["outcome_key"] not in graded_keys]
    if not pending:
        raise HTTPException(400, "No pending outcomes for GRADE assessment")

    job = create_job(review_id, total=len(pending))
    llm = criar_llm(model=body.model, temperature=body.temperature)

    async def _bg():
        extractions = await repo.get_extractions(review_id)
        protocolo = await repo.get_protocol(review_id) or {}

        try:
            envelopes, metricas = await asyncio.to_thread(
                assess_grade, pending, extractions, protocolo, llm,
            )
        except Exception as e:
            logger.error("GRADE failed: %s", e)
            j = get_job(job.id)
            if j:
                j.status = "failed"
            publish_event(job.id, {"type": "done"})
            return

        for env in envelopes:
            gr = env.resultado
            grade_data = {
                "outcome_key": gr.outcome_key,
                "starting_certainty": gr.starting_certainty,
                "domain_results": [d.model_dump() for d in gr.domains],
                "final_certainty": gr.final_certainty,
                "k_studies": next((s["k_studies"] for s in pending if s["outcome_key"] == gr.outcome_key), 0),
                "status": "draft",
                "degradado": env.degradado,
                "alertas": env.alertas,
            }
            await repo.add_grade_assessment(review_id, grade_data)

        await repo.add_trace(review_id, metricas)
        j = get_job(job.id)
        if j:
            j.status = "completed"
        publish_event(job.id, {"type": "done"})

    asyncio.get_event_loop().create_task(_bg())
    return JobResponse(job_id=job.id, status=job.status, progress=0, total=job.total)


@router.get("/{review_id}/grade", response_model=list[GradeAssessmentResponse])
async def list_grade_assessments(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    assessments = await repo.get_grade_assessments(review_id)
    results = []
    for a in assessments:
        domains = [GradeDomainResponse(**d) for d in a.get("domain_results", [])]
        results.append(GradeAssessmentResponse(
            outcome_key=a["outcome_key"],
            starting_certainty=a.get("starting_certainty", "high"),
            domains=domains,
            final_certainty=a.get("final_certainty", "high"),
            k_studies=a.get("k_studies", 0),
            status=a.get("status", "draft"),
            degradado=a.get("degradado", False),
            alertas=a.get("alertas", []),
        ))
    return results


@router.get("/{review_id}/grade/sof", response_model=SofResponse)
async def get_summary_of_findings(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    syntheses = await repo.get_syntheses(review_id)
    grades = await repo.get_grade_assessments(review_id)
    grade_by_key = {g["outcome_key"]: g for g in grades}

    entries = []
    for syn in syntheses:
        ok = syn["outcome_key"]
        grade = grade_by_key.get(ok, {})
        domains = grade.get("domain_results", [])

        def _get_downgrade(domain_name: str) -> int:
            for d in domains:
                if d.get("domain") == domain_name:
                    return d.get("rating", 0)
            return 0

        entries.append(SofEntry(
            outcome_key=ok,
            measure=syn.get("measure", ""),
            k_studies=syn.get("k_studies", 0),
            n_participants=syn.get("n_participants"),
            pooled_effect=syn.get("pooled_effect"),
            ci_low=syn.get("ci_low"),
            ci_high=syn.get("ci_high"),
            certainty=grade.get("final_certainty", ""),
            rob_downgrade=_get_downgrade("risk_of_bias"),
            inconsistency_downgrade=_get_downgrade("inconsistency"),
            indirectness_downgrade=_get_downgrade("indirectness"),
            imprecision_downgrade=_get_downgrade("imprecision"),
            pub_bias_downgrade=_get_downgrade("publication_bias"),
        ))
    return SofResponse(entries=entries)


@router.post("/{review_id}/grade/{outcome_key}/approve")
async def approve_grade(
    review_id: str,
    outcome_key: str,
    repo: ReviewRepository = Depends(get_repo),
):
    await repo.approve_grade(review_id, outcome_key, approved_by="api")
    return {"status": "approved"}
