from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.schemas import (
    CreateReviewRequest,
    ImportRecordsRequest,
    ImportResponse,
    ProtocolRequest,
)
from prismai.persistence.repository import ReviewRepository

router = APIRouter(prefix="/v1/reviews", tags=["reviews"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_reviews(repo: ReviewRepository = Depends(get_repo)):
    return await repo.list_reviews()


@router.get("/{review_id}")
async def get_review(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, "Review not found")
    return review


@router.post("", status_code=201)
async def create_review(body: CreateReviewRequest, repo: ReviewRepository = Depends(get_repo)):
    try:
        return await repo.create_review(body.id)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


@router.post("/{review_id}/protocol")
async def set_protocol(review_id: str, body: ProtocolRequest, repo: ReviewRepository = Depends(get_repo)):
    try:
        await repo.set_protocol(review_id, body.model_dump())
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return {"ok": True}


@router.get("/{review_id}/protocol")
async def get_protocol(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    proto = await repo.get_protocol(review_id)
    if proto is None:
        raise HTTPException(404, "Protocol not set")
    return proto


@router.post("/{review_id}/records", response_model=ImportResponse)
async def import_records(review_id: str, body: ImportRecordsRequest, repo: ReviewRepository = Depends(get_repo)):
    raw = [r.model_dump() for r in body.records]
    try:
        new_records, dup_count = await _dedup_if_possible(review_id, raw, repo)
        n = await repo.add_records(review_id, new_records) if new_records else 0
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    await repo.add_import_run(review_id, {
        "source": "manual", "total_found": len(body.records), "imported": n, "duplicates": 0,
    })
    return ImportResponse(imported=n, duplicates=dup_count)


async def _dedup_if_possible(
    review_id: str, records: list[dict], repo: ReviewRepository,
) -> tuple[list[dict], int]:
    """Try to deduplicate via DB session; fall back to no-dedup for InMemory."""
    from prismai.persistence.postgres import PostgresRepository

    if not isinstance(repo, PostgresRepository):
        return records, 0

    from sqlalchemy import select as sa_select

    from prismai.connectors.dedup import deduplicate
    from prismai.persistence.engine import async_session_factory
    from prismai.persistence.models_db import Review

    async with async_session_factory() as session:
        review_row = (await session.execute(
            sa_select(Review).where(Review.slug == review_id)
        )).scalar_one_or_none()
        if review_row is None:
            return records, 0
        new, dups = await deduplicate(session, review_row.id, records)
    return new, len(dups)


@router.get("/{review_id}/decisions")
async def get_decisions(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    return await repo.get_decisions(review_id)


@router.get("/{review_id}/traces")
async def get_traces(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    return await repo.get_traces(review_id)
