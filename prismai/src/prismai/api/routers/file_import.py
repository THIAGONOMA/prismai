from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from prismai.api.deps import get_repo
from prismai.api.schemas import FileImportResponse
from prismai.connectors.file_import import detect_and_parse
from prismai.persistence.repository import ReviewRepository

router = APIRouter(prefix="/v1/reviews", tags=["import"])
logger = logging.getLogger(__name__)


@router.post("/{review_id}/import", response_model=FileImportResponse)
async def import_file(
    review_id: str,
    file: UploadFile,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")

    content = await file.read()
    filename = file.filename or "unknown.csv"

    try:
        records, fmt = detect_and_parse(content, filename)
    except Exception as e:
        logger.exception("Failed to parse uploaded file %s", filename)
        raise HTTPException(400, f"Erro ao processar arquivo: {e}") from e

    if not records:
        return FileImportResponse(imported=0, duplicates=0, format=fmt)

    from prismai.api.routers.reviews import _dedup_if_possible

    new_records, dup_count = await _dedup_if_possible(review_id, records, repo)
    imported = await repo.add_records(review_id, new_records) if new_records else 0

    await repo.add_import_run(review_id, {
        "source": "file", "filename": filename,
        "total_found": len(records), "imported": imported, "duplicates": dup_count,
    })

    return FileImportResponse(imported=imported, duplicates=dup_count, format=fmt)
