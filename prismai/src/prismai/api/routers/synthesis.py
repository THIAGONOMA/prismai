"""Router for quantitative synthesis / meta-analysis (M6)."""
from __future__ import annotations

import asyncio
import logging
import tempfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from prismai.api.deps import get_repo
from prismai.api.jobs import create_job, get_job, publish_event
from prismai.api.schemas import (
    JobResponse,
    RunSynthesisRequest,
    SynthesisConfigRequest,
    SynthesisResponse,
)
from prismai.core.synthesis_config import carregar_synthesis_config
from prismai.graphs.synthesis import synthesize
from prismai.llm.client import criar_llm
from prismai.persistence.repository import ReviewRepository
from prismai.synthesis.plot import forest_data, funnel_data_for_plot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/reviews", tags=["synthesis"])


@router.post("/{review_id}/synthesis-config", status_code=200)
async def set_synthesis_config(
    review_id: str,
    body: SynthesisConfigRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")
    carregar_synthesis_config(body.config)
    await repo.set_synthesis_config(review_id, body.config)
    return {"status": "ok"}


@router.get("/{review_id}/synthesis-config")
async def get_synthesis_config(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    config = await repo.get_synthesis_config(review_id)
    return {"config": config}


@router.post("/{review_id}/synthesis/run", response_model=JobResponse, status_code=202)
async def run_synthesis(
    review_id: str,
    body: RunSynthesisRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")

    config_raw = await repo.get_synthesis_config(review_id)
    config = carregar_synthesis_config(config_raw)
    if config is None:
        raise HTTPException(400, "Synthesis config not set")

    existing = await repo.get_syntheses(review_id)
    done_keys = {s["outcome_key"] for s in existing}
    pending = [oc for oc in config.outcomes if oc.key not in done_keys]
    if not pending:
        raise HTTPException(400, "No pending outcomes for synthesis")

    job = create_job(review_id, total=len(pending))
    llm = criar_llm(model=body.model, temperature=body.temperature)

    async def _bg():
        extractions = await repo.get_extractions(review_id)
        full_extractions = []
        for ext in extractions:
            if ext.get("status") != "completed":
                continue
            full = await repo.get_extraction(review_id, ext["record_id"])
            if full:
                full_extractions.append(full)

        rob_assessments = await repo.get_rob_assessments(review_id)
        protocolo = await repo.get_protocol(review_id) or {}
        pending_config = {"version": config.version, "outcomes": [oc.model_dump() for oc in pending]}

        try:
            envelopes, metricas = await asyncio.to_thread(
                synthesize, pending_config, full_extractions, rob_assessments, protocolo, llm,
            )
        except Exception as e:
            logger.error("Synthesis failed: %s", e)
            j = get_job(job.id)
            if j:
                j.status = "failed"
            publish_event(job.id, {"type": "done"})
            return

        for env in envelopes:
            sr = env.resultado
            syn_data = {
                "outcome_key": sr.outcome_key,
                "measure": sr.measure,
                "model": sr.model,
                "k_studies": sr.k_studies,
                "pooled_effect": sr.pooled_effect,
                "se": sr.se,
                "ci_low": sr.ci_low,
                "ci_high": sr.ci_high,
                "p_value": sr.p_value,
                "tau2": sr.tau2,
                "q": sr.q,
                "i2": sr.i2,
                "prediction_low": sr.prediction_low,
                "prediction_high": sr.prediction_high,
                "egger_intercept": sr.egger_intercept,
                "egger_p": sr.egger_p,
                "study_effects": [s.model_dump() for s in sr.study_effects],
                "status": "draft",
                "degradado": env.degradado,
                "alertas": env.alertas,
            }
            await repo.add_synthesis(review_id, syn_data)

        await repo.add_trace(review_id, metricas)
        j = get_job(job.id)
        if j:
            j.status = "completed"
        publish_event(job.id, {"type": "done"})

    asyncio.get_event_loop().create_task(_bg())
    return JobResponse(job_id=job.id, status=job.status, progress=0, total=job.total)


@router.get("/{review_id}/synthesis", response_model=list[SynthesisResponse])
async def list_syntheses(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    syntheses = await repo.get_syntheses(review_id)
    return [SynthesisResponse(**s) for s in syntheses]


@router.get("/{review_id}/synthesis/{outcome_key}", response_model=SynthesisResponse)
async def get_synthesis_detail(
    review_id: str,
    outcome_key: str,
    repo: ReviewRepository = Depends(get_repo),
):
    syn = await repo.get_synthesis(review_id, outcome_key)
    if syn is None:
        raise HTTPException(404, f"Synthesis for outcome '{outcome_key}' not found")
    return SynthesisResponse(**syn)


@router.post("/{review_id}/synthesis/{outcome_key}/approve")
async def approve_synthesis(
    review_id: str,
    outcome_key: str,
    repo: ReviewRepository = Depends(get_repo),
):
    await repo.approve_synthesis(review_id, outcome_key, approved_by="api")
    return {"status": "approved"}


@router.get("/{review_id}/synthesis/{outcome_key}/forest")
async def get_forest_data(
    review_id: str,
    outcome_key: str,
    repo: ReviewRepository = Depends(get_repo),
):
    syn = await repo.get_synthesis(review_id, outcome_key)
    if syn is None:
        raise HTTPException(404, f"Synthesis for outcome '{outcome_key}' not found")
    data = forest_data(syn.get("study_effects", []), syn, syn.get("measure", ""))
    return data


@router.get("/{review_id}/synthesis/{outcome_key}/funnel")
async def get_funnel_data(
    review_id: str,
    outcome_key: str,
    repo: ReviewRepository = Depends(get_repo),
):
    syn = await repo.get_synthesis(review_id, outcome_key)
    if syn is None:
        raise HTTPException(404, f"Synthesis for outcome '{outcome_key}' not found")
    data = funnel_data_for_plot(syn.get("study_effects", []), syn.get("pooled_effect", 0))
    return data


@router.get("/{review_id}/synthesis/{outcome_key}/forest.png")
async def get_forest_png(
    review_id: str,
    outcome_key: str,
    repo: ReviewRepository = Depends(get_repo),
):
    from prismai.synthesis.plot import render_forest_png

    syn = await repo.get_synthesis(review_id, outcome_key)
    if syn is None:
        raise HTTPException(404, f"Synthesis for outcome '{outcome_key}' not found")
    data = forest_data(syn.get("study_effects", []), syn, syn.get("measure", ""))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_forest_png(data, path)
    except ImportError as e:
        raise HTTPException(501, str(e))
    return FileResponse(path, media_type="image/png")


@router.get("/{review_id}/synthesis/{outcome_key}/funnel.png")
async def get_funnel_png(
    review_id: str,
    outcome_key: str,
    repo: ReviewRepository = Depends(get_repo),
):
    from prismai.synthesis.plot import render_funnel_png

    syn = await repo.get_synthesis(review_id, outcome_key)
    if syn is None:
        raise HTTPException(404, f"Synthesis for outcome '{outcome_key}' not found")
    data = funnel_data_for_plot(syn.get("study_effects", []), syn.get("pooled_effect", 0))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        render_funnel_png(data, path)
    except ImportError as e:
        raise HTTPException(501, str(e))
    return FileResponse(path, media_type="image/png")
