"""API router for living review (F12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.schemas import (
    EnableLivingRequest,
    JobResponse,
    LivingStatusResponse,
    LivingUpdateResponse,
    RunLivingRequest,
)
from prismai.persistence.repository import ReviewRepository

router = APIRouter(prefix="/v1/reviews", tags=["living"])


@router.post("/{review_id}/living/enable")
async def enable_living(
    review_id: str,
    body: EnableLivingRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")
    await repo.enable_living(review_id, body.cron)
    return {"status": "enabled", "cron": body.cron}


@router.post("/{review_id}/living/disable")
async def disable_living(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")
    await repo.disable_living(review_id)
    return {"status": "disabled"}


@router.post("/{review_id}/living/run", response_model=JobResponse, status_code=202)
async def run_living_update(
    review_id: str,
    body: RunLivingRequest | None = None,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")

    from prismai.api.jobs import create_job

    job = create_job(review_id, total=1)
    model = body.model if body else "gpt-4o-mini"
    temperature = body.temperature if body else 0

    try:
        from prismai.queue.settings import queue
        from prismai.queue.tasks import run_living_update_task

        await queue.enqueue(
            run_living_update_task,
            job_id=job.id, review_id=review_id, org_id="",
            trigger="manual", model=model, temperature=temperature,
        )
    except Exception:
        import asyncio

        from prismai.queue.tasks import run_living_update_task

        asyncio.create_task(run_living_update_task(
            {}, job_id=job.id, review_id=review_id, org_id="",
            trigger="manual", model=model, temperature=temperature,
        ))

    return JobResponse(job_id=job.id, status="pending")


@router.get("/{review_id}/living/updates", response_model=list[LivingUpdateResponse])
async def list_living_updates(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")
    updates = await repo.get_living_updates(review_id)
    return updates


@router.get("/{review_id}/living/status", response_model=LivingStatusResponse)
async def get_living_status(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")
    updates = await repo.get_living_updates(review_id)
    last_update = updates[-1] if updates else None
    living_reviews = await repo.get_living_reviews()
    is_enabled = any(r["id"] == review_id for r in living_reviews)
    cron = next((r.get("living_cron") for r in living_reviews if r["id"] == review_id), None)
    return LivingStatusResponse(
        enabled=is_enabled,
        cron=cron,
        total_updates=len(updates),
        last_update=last_update,
        pending_notifications=sum(1 for u in updates if not u.get("notified", True)),
    )
