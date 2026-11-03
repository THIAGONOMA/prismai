"""Router for full-text document management (F5)."""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from prismai.api.deps import get_repo
from prismai.api.jobs import create_job
from prismai.api.schemas import DocumentResponse, FulltextFetchResponse
from prismai.config import settings
from prismai.persistence.repository import ReviewRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/reviews", tags=["documents"])


@router.post("/{review_id}/fulltext/fetch", response_model=FulltextFetchResponse, status_code=202)
async def trigger_fulltext_fetch(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")

    decisions = await repo.get_decisions(review_id)
    included = [d for d in decisions if d["decision"] == "include"]
    if not included:
        raise HTTPException(400, "No included records to fetch")

    job = create_job(review_id, total=len(included))

    async def _bg():
        from prismai.api.jobs import get_job, publish_event
        from prismai.connectors.grobid import extract_document
        from prismai.connectors.ocr_check import estimate_ocr_confidence
        from prismai.connectors.pdf_fetcher import fetch_pdf

        records = await repo.get_records(review_id)
        included_ids = {d["registro_id"] for d in included}
        pending = [r for r in records if r["id"] in included_ids]

        for i, rec in enumerate(pending):
            existing = await repo.get_document(review_id, rec["id"])
            if existing is not None:
                continue

            doc_data: dict = {"record_id": rec["id"], "status": "pending"}
            result = await fetch_pdf(
                rec, settings.pdf_storage_path,
                review_id=review_id, timeout=settings.fulltext_fetch_timeout_s,
            )
            if not result["path"]:
                doc_data["status"] = "failed"
                doc_data["error"] = result.get("error", "PDF not found")
                await repo.add_document(review_id, doc_data)
                continue

            doc_data["storage_path"] = result["path"]
            doc_data["fetch_source"] = result["source"]

            try:
                extracted = await extract_document(result["path"], settings.grobid_url, settings.grobid_timeout_s)
                doc_data.update({
                    "content_text": extracted["content_text"],
                    "sections": extracted["sections"],
                    "n_pages": extracted["n_pages"],
                    "extraction_method": "grobid",
                    "status": "extracted",
                })
            except Exception:
                doc_data["status"] = "fetched"

            ocr_conf = estimate_ocr_confidence(result["path"])
            doc_data["ocr_confidence"] = ocr_conf
            if ocr_conf < settings.ocr_confidence_threshold:
                doc_data["status"] = "requires_manual_transcription"

            await repo.add_document(review_id, doc_data)
            j = get_job(job.id)
            if j:
                j.progress = i + 1
            publish_event(job.id, {"type": "progress", "progress": i + 1})

        j = get_job(job.id)
        if j:
            j.status = "completed"
        publish_event(job.id, {"type": "done"})

    asyncio.get_event_loop().create_task(_bg())
    return FulltextFetchResponse(job_id=job.id, status="running")


@router.get("/{review_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    review_id: str,
    status: str | None = None,
    repo: ReviewRepository = Depends(get_repo),
):
    docs = await repo.get_documents(review_id, status=status)
    return [DocumentResponse(**{k: v for k, v in d.items() if k in DocumentResponse.model_fields}) for d in docs]


@router.get("/{review_id}/documents/{record_id}", response_model=DocumentResponse)
async def get_document(
    review_id: str,
    record_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    doc = await repo.get_document(review_id, record_id)
    if doc is None:
        raise HTTPException(404, f"Document for record '{record_id}' not found")
    return DocumentResponse(**{k: v for k, v in doc.items() if k in DocumentResponse.model_fields})


@router.post("/{review_id}/documents/{record_id}/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    review_id: str,
    record_id: str,
    file: UploadFile,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")

    dest_dir = Path(settings.pdf_storage_path) / review_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{record_id}.pdf"

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc_data = {
        "record_id": record_id,
        "storage_path": str(dest),
        "fetch_source": "manual",
        "status": "fetched",
    }

    existing = await repo.get_document(review_id, record_id)
    if existing:
        await repo.update_document(review_id, record_id, doc_data)
    else:
        await repo.add_document(review_id, doc_data)

    doc = await repo.get_document(review_id, record_id)
    return DocumentResponse(**{k: v for k, v in doc.items() if k in DocumentResponse.model_fields})
