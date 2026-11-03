from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.schemas import SearchRequest, SearchResponse
from prismai.config import settings
from prismai.persistence.repository import ReviewRepository

router = APIRouter(prefix="/v1/reviews", tags=["search"])
logger = logging.getLogger(__name__)


@router.post("/{review_id}/search", response_model=SearchResponse)
async def search_and_import(
    review_id: str,
    body: SearchRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")

    if body.source == "openalex":
        from prismai.connectors.openalex import buscar_openalex

        found = await buscar_openalex(
            body.query,
            max_results=body.max_results,
            api_key=settings.openalex_api_key or None,
        )
    elif body.source == "crossref":
        from prismai.connectors.crossref import buscar_crossref

        found = await buscar_crossref(body.query, max_results=body.max_results)
    else:
        raise HTTPException(400, f"Fonte '{body.source}' não suportada. Use 'openalex' ou 'crossref'.")

    total_found = len(found)

    from prismai.api.routers.reviews import _dedup_if_possible

    new_records, dup_count = await _dedup_if_possible(review_id, found, repo)
    imported = await repo.add_records(review_id, new_records) if new_records else 0

    await repo.add_import_run(review_id, {
        "source": body.source, "query": body.query,
        "total_found": total_found, "imported": imported, "duplicates": dup_count,
    })

    return SearchResponse(imported=imported, duplicates=dup_count, total_found=total_found)
