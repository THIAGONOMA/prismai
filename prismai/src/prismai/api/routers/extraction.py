"""Router for structured data extraction (F7)."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.jobs import create_job, get_job, publish_event
from prismai.api.schemas import (
    ExtractionCellResponse,
    ExtractionResponse,
    ExtractionSchemaRequest,
    JobResponse,
    RunExtractionRequest,
)
from prismai.core.extraction_schema import carregar_schema
from prismai.graphs.extraction import extract_data
from prismai.llm.client import criar_llm
from prismai.persistence.repository import ReviewRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/reviews", tags=["extraction"])


@router.post("/{review_id}/extraction/run", response_model=JobResponse, status_code=202)
async def run_extraction(
    review_id: str,
    body: RunExtractionRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")

    elig = await repo.get_eligibility_decisions(review_id)
    included_ids = {d["record_id"] for d in elig if d["decision"] == "include"}
    if not included_ids:
        raise HTTPException(400, "No included documents for extraction")

    existing = await repo.get_extractions(review_id)
    done_ids = {e["record_id"] for e in existing}
    pending_ids = included_ids - done_ids

    docs = await repo.get_documents(review_id, status="extracted")
    pending_docs = [d for d in docs if d.get("record_id") in pending_ids]
    if not pending_docs:
        raise HTTPException(400, "No pending documents for extraction")

    job = create_job(review_id, total=len(pending_docs))
    schema_raw = await repo.get_extraction_schema(review_id)
    schema = carregar_schema(schema_raw)
    llm = criar_llm(model=body.model, temperature=body.temperature)

    async def _bg():
        records = await repo.get_records(review_id)
        records_by_id = {r["id"]: r for r in records}

        for i, doc in enumerate(pending_docs):
            record_id = doc.get("record_id", "")
            record = records_by_id.get(record_id, {"id": record_id})

            try:
                resposta, metricas = await asyncio.to_thread(
                    extract_data, doc, record, schema.model_dump(), llm,
                )
            except Exception as e:
                logger.error("Extraction failed for %s: %s", record_id, e)
                continue

            extraction_data = {
                "record_id": record_id,
                "schema_version": resposta.resultado.schema_version,
                "status": "completed",
                "degradado": resposta.degradado,
                "alertas": resposta.alertas,
                "cells": [
                    {
                        "field": c.field, "block": c.block, "value": c.value,
                        "value_type": c.value_type,
                        "confidence": c.confidence,
                        "needs_human_confirmation": c.needs_human_confirmation,
                        "flags": c.flags,
                    }
                    for c in resposta.resultado.cells
                ],
            }
            await repo.add_extraction(review_id, extraction_data)
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


@router.get("/{review_id}/extraction", response_model=list[ExtractionResponse])
async def list_extractions(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    extractions = await repo.get_extractions(review_id)
    return [ExtractionResponse(**e) for e in extractions]


@router.get("/{review_id}/extraction/{record_id}", response_model=ExtractionResponse)
async def get_extraction(
    review_id: str,
    record_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    ext = await repo.get_extraction(review_id, record_id)
    if ext is None:
        raise HTTPException(404, f"Extraction for record '{record_id}' not found")
    return ExtractionResponse(
        record_id=ext["record_id"],
        schema_version=ext.get("schema_version", ""),
        status=ext.get("status", ""),
        cells=[ExtractionCellResponse(**c) for c in ext.get("cells", [])],
        degradado=ext.get("degradado", False),
        alertas=ext.get("alertas", []),
    )


@router.post("/{review_id}/extraction-schema", status_code=200)
async def set_extraction_schema(
    review_id: str,
    body: ExtractionSchemaRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")
    carregar_schema(body.schema_data)
    await repo.set_extraction_schema(review_id, body.schema_data)
    return {"status": "ok"}


@router.get("/{review_id}/extraction-schema")
async def get_extraction_schema(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    schema = await repo.get_extraction_schema(review_id)
    if schema is None:
        return {"schema": None, "default": carregar_schema(None).model_dump()}
    return {"schema": schema}
