from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from prismai.persistence import models_db as m
from prismai.text.normalize import normalizar


class PostgresRepository:
    """ReviewRepository implementation backed by PostgreSQL via SQLAlchemy async.

    For contract-test purposes this operates without RLS (no org_id filtering).
    The API layer sets org context via ``set_config`` before calling repo methods,
    and RLS policies handle tenant isolation transparently.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def create_review(self, review_id: str) -> dict:
        async with self._sf() as session:
            async with session.begin():
                existing = (await session.execute(
                    select(m.Review).where(m.Review.slug == review_id)
                )).scalar_one_or_none()
                if existing is not None:
                    raise ValueError(f"Review '{review_id}' already exists")

                review = m.Review(slug=review_id)
                session.add(review)
                await session.flush()
                return {
                    "id": review.slug,
                    "created_at": review.created_at.isoformat(),
                    "living_enabled": review.living_enabled,
                    "living_cron": review.living_cron,
                }

    async def get_review(self, review_id: str) -> dict | None:
        async with self._sf() as session:
            row = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if row is None:
                return None
            return {"id": row.slug, "created_at": row.created_at.isoformat()}

    async def _get_review_or_raise(self, session: AsyncSession, review_id: str) -> m.Review:
        row = (await session.execute(
            select(m.Review).where(m.Review.slug == review_id)
        )).scalar_one_or_none()
        if row is None:
            raise KeyError(f"Review '{review_id}' not found")
        return row

    async def set_protocol(self, review_id: str, protocol: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                existing = (await session.execute(
                    select(m.Protocol).where(m.Protocol.review_id == review.id)
                )).scalar_one_or_none()
                if existing is not None:
                    existing.data = protocol
                else:
                    session.add(m.Protocol(
                        org_id=review.org_id, review_id=review.id, data=protocol,
                    ))

    async def get_protocol(self, review_id: str) -> dict | None:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return None
            row = (await session.execute(
                select(m.Protocol).where(m.Protocol.review_id == review.id)
            )).scalar_one_or_none()
            return row.data if row else None

    async def add_records(self, review_id: str, records: list[dict]) -> int:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                for rec in records:
                    titulo = rec.get("titulo", "")
                    session.add(m.Record(
                        org_id=review.org_id,
                        review_id=review.id,
                        external_id=rec.get("id", ""),
                        titulo=titulo,
                        abstract=rec.get("abstract", ""),
                        doi=rec.get("doi"),
                        authors=rec.get("authors", []),
                        year=rec.get("year"),
                        source=rec.get("source", "manual"),
                        title_norm=normalizar(titulo) if titulo else None,
                    ))
                return len(records)

    async def get_records(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.Record).where(m.Record.review_id == review.id)
            )).scalars().all()
            return [
                {
                    "id": r.external_id, "titulo": r.titulo, "abstract": r.abstract,
                    "doi": r.doi, "authors": r.authors, "year": r.year, "source": r.source,
                }
                for r in rows
            ]

    async def add_decision(self, review_id: str, decision: dict, screener: str = "primary") -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                session.add(m.Decision(
                    org_id=review.org_id,
                    review_id=review.id,
                    registro_id=decision.get("registro_id", ""),
                    screener=screener,
                    decision=decision.get("decision", ""),
                    confidence=decision.get("confidence", ""),
                    reasons=decision.get("reasons", []),
                    evidence=decision.get("evidence", []),
                    degradado=decision.get("degradado", False),
                    alertas=decision.get("alertas", []),
                ))

    async def get_decisions(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.Decision).where(m.Decision.review_id == review.id)
            )).scalars().all()
            return [
                {
                    "registro_id": d.registro_id,
                    "screener": d.screener,
                    "decision": d.decision,
                    "confidence": d.confidence,
                    "reasons": d.reasons,
                    "evidence": d.evidence,
                    "degradado": d.degradado,
                    "alertas": d.alertas,
                }
                for d in rows
            ]

    async def get_decided_registro_ids(self, review_id: str, screener: str | None = None) -> set[str]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return set()
            stmt = select(m.Decision.registro_id).where(m.Decision.review_id == review.id)
            if screener is not None:
                stmt = stmt.where(m.Decision.screener == screener)
            rows = (await session.execute(stmt)).scalars().all()
            return set(rows)

    async def add_conflict(self, review_id: str, conflict: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                session.add(m.Conflict(
                    org_id=review.org_id,
                    review_id=review.id,
                    registro_id=conflict["registro_id"],
                    decision_a=conflict["decision_a"],
                    decision_b=conflict["decision_b"],
                    screener_a=conflict["screener_a"],
                    screener_b=conflict["screener_b"],
                    disagreement_score=conflict.get("disagreement_score", 0.0),
                    status=conflict.get("status", "pending"),
                ))

    async def get_conflicts(self, review_id: str, status: str | None = None) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            stmt = select(m.Conflict).where(m.Conflict.review_id == review.id)
            if status is not None:
                stmt = stmt.where(m.Conflict.status == status)
            stmt = stmt.order_by(m.Conflict.disagreement_score.desc())
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "registro_id": c.registro_id,
                    "decision_a": c.decision_a, "decision_b": c.decision_b,
                    "screener_a": c.screener_a, "screener_b": c.screener_b,
                    "disagreement_score": c.disagreement_score,
                    "status": c.status,
                    "resolved_decision": c.resolved_decision,
                    "resolved_note": c.resolved_note,
                    "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                }
                for c in rows
            ]

    async def resolve_conflict(self, review_id: str, registro_id: str, decision: str, note: str) -> None:
        from datetime import datetime, timezone

        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                row = (await session.execute(
                    select(m.Conflict).where(
                        m.Conflict.review_id == review.id,
                        m.Conflict.registro_id == registro_id,
                    )
                )).scalar_one_or_none()
                if row is None:
                    raise KeyError(f"Conflict for registro '{registro_id}' not found")
                row.status = "resolved"
                row.resolved_decision = decision
                row.resolved_note = note
                row.resolved_at = datetime.now(timezone.utc)

    async def add_document(self, review_id: str, document: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                record = (await session.execute(
                    select(m.Record).where(
                        m.Record.review_id == review.id,
                        m.Record.external_id == document["record_id"],
                    )
                )).scalar_one_or_none()
                record_uuid = record.id if record else None
                session.add(m.Document(
                    org_id=review.org_id,
                    review_id=review.id,
                    record_id=record_uuid,
                    storage_path=document.get("storage_path"),
                    content_text=document.get("content_text"),
                    sections=document.get("sections", []),
                    n_pages=document.get("n_pages", 0),
                    ocr_confidence=document.get("ocr_confidence"),
                    extraction_method=document.get("extraction_method"),
                    status=document.get("status", "pending"),
                    fetch_source=document.get("fetch_source"),
                    error=document.get("error"),
                ))

    async def get_document(self, review_id: str, record_id: str) -> dict | None:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return None
            record = (await session.execute(
                select(m.Record).where(
                    m.Record.review_id == review.id,
                    m.Record.external_id == record_id,
                )
            )).scalar_one_or_none()
            if record is None:
                return None
            doc = (await session.execute(
                select(m.Document).where(
                    m.Document.review_id == review.id,
                    m.Document.record_id == record.id,
                )
            )).scalar_one_or_none()
            if doc is None:
                return None
            return self._doc_to_dict(doc, record_id)

    async def get_documents(self, review_id: str, status: str | None = None) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            stmt = select(m.Document).where(m.Document.review_id == review.id)
            if status is not None:
                stmt = stmt.where(m.Document.status == status)
            rows = (await session.execute(stmt)).scalars().all()
            record_ids = {r.id: r.external_id for r in (await session.execute(
                select(m.Record).where(m.Record.review_id == review.id)
            )).scalars().all()}
            return [self._doc_to_dict(d, record_ids.get(d.record_id, "")) for d in rows]

    async def update_document(self, review_id: str, record_id: str, updates: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                record = (await session.execute(
                    select(m.Record).where(
                        m.Record.review_id == review.id,
                        m.Record.external_id == record_id,
                    )
                )).scalar_one_or_none()
                if record is None:
                    raise KeyError(f"Record '{record_id}' not found")
                doc = (await session.execute(
                    select(m.Document).where(
                        m.Document.review_id == review.id,
                        m.Document.record_id == record.id,
                    )
                )).scalar_one_or_none()
                if doc is None:
                    raise KeyError(f"Document for record '{record_id}' not found")
                for k, v in updates.items():
                    if hasattr(doc, k):
                        setattr(doc, k, v)

    async def add_eligibility_decision(self, review_id: str, decision: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                record = (await session.execute(
                    select(m.Record).where(
                        m.Record.review_id == review.id,
                        m.Record.external_id == decision["record_id"],
                    )
                )).scalar_one_or_none()
                doc = (await session.execute(
                    select(m.Document).where(
                        m.Document.review_id == review.id,
                        m.Document.record_id == record.id if record else None,
                    )
                )).scalar_one_or_none()
                session.add(m.EligibilityDecision(
                    org_id=review.org_id,
                    review_id=review.id,
                    document_id=doc.id if doc else None,
                    decision=decision.get("decision", ""),
                    exclusion_reason=decision.get("exclusion_reason"),
                    confidence=decision.get("confidence", ""),
                    reasons=decision.get("reasons", []),
                    degradado=decision.get("degradado", False),
                    alertas=decision.get("alertas", []),
                ))

    async def get_eligibility_decisions(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.EligibilityDecision).where(m.EligibilityDecision.review_id == review.id)
            )).scalars().all()
            doc_ids = {d.id for d in rows}
            record_map: dict[uuid.UUID, str] = {}
            if doc_ids:
                docs = (await session.execute(
                    select(m.Document).where(m.Document.review_id == review.id)
                )).scalars().all()
                rec_ids = {r.id: r.external_id for r in (await session.execute(
                    select(m.Record).where(m.Record.review_id == review.id)
                )).scalars().all()}
                for doc in docs:
                    record_map[doc.id] = rec_ids.get(doc.record_id, "")
            return [
                {
                    "document_id": str(d.document_id),
                    "record_id": record_map.get(d.document_id, ""),
                    "decision": d.decision,
                    "exclusion_reason": d.exclusion_reason,
                    "confidence": d.confidence,
                    "reasons": d.reasons,
                    "degradado": d.degradado,
                    "alertas": d.alertas,
                }
                for d in rows
            ]

    async def _resolve_document_id(
        self, session: AsyncSession, review: m.Review, record_id: str,
    ) -> uuid.UUID:
        record = (await session.execute(
            select(m.Record).where(m.Record.review_id == review.id, m.Record.external_id == record_id)
        )).scalar_one_or_none()
        if record is None:
            raise KeyError(f"Record '{record_id}' not found")
        doc = (await session.execute(
            select(m.Document).where(m.Document.review_id == review.id, m.Document.record_id == record.id)
        )).scalar_one_or_none()
        if doc is None:
            raise KeyError(f"Document for record '{record_id}' not found")
        return doc.id

    async def add_evidence_span(self, review_id: str, span: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                doc_id = await self._resolve_document_id(session, review, span["record_id"])
                session.add(m.EvidenceSpan(
                    org_id=review.org_id,
                    document_id=doc_id,
                    page=span["page"],
                    start_offset=span["start"],
                    end_offset=span["end"],
                    text=span["text"],
                    criterion=span["criterion"],
                ))

    @staticmethod
    def _doc_to_dict(doc: m.Document, record_id: str) -> dict:
        return {
            "record_id": record_id,
            "status": doc.status,
            "storage_path": doc.storage_path,
            "content_text": doc.content_text,
            "sections": doc.sections,
            "n_pages": doc.n_pages,
            "ocr_confidence": doc.ocr_confidence,
            "extraction_method": doc.extraction_method,
            "fetch_source": doc.fetch_source,
            "error": doc.error,
        }

    async def add_trace(self, review_id: str, trace: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                session.add(m.Trace(
                    org_id=review.org_id, review_id=review.id, data=trace,
                ))

    async def get_traces(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.Trace).where(m.Trace.review_id == review.id)
            )).scalars().all()
            return [r.data for r in rows]

    async def get_evidence_spans(self, review_id: str, record_id: str | None = None) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            stmt = (
                select(m.EvidenceSpan)
                .join(m.Document, m.EvidenceSpan.document_id == m.Document.id)
                .where(m.Document.review_id == review.id)
            )
            if record_id is not None:
                record = (await session.execute(
                    select(m.Record).where(
                        m.Record.review_id == review.id, m.Record.external_id == record_id,
                    )
                )).scalar_one_or_none()
                if record is None:
                    return []
                stmt = stmt.where(m.Document.record_id == record.id)
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "page": s.page, "start": s.start_offset, "end": s.end_offset,
                    "text": s.text, "criterion": s.criterion,
                }
                for s in rows
            ]

    async def set_extraction_schema(self, review_id: str, schema: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                proto = (await session.execute(
                    select(m.Protocol).where(m.Protocol.review_id == review.id)
                )).scalar_one_or_none()
                if proto is None:
                    raise KeyError(f"Protocol not set for review '{review_id}'")
                proto.extraction_schema = schema

    async def get_extraction_schema(self, review_id: str) -> dict | None:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return None
            proto = (await session.execute(
                select(m.Protocol).where(m.Protocol.review_id == review.id)
            )).scalar_one_or_none()
            if proto is None:
                return None
            return proto.extraction_schema

    async def add_extraction(self, review_id: str, extraction: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                doc_id = await self._resolve_document_id(session, review, extraction["record_id"])
                ext = m.Extraction(
                    org_id=review.org_id,
                    review_id=review.id,
                    document_id=doc_id,
                    schema_version=extraction.get("schema_version", "cochrane-default-v2"),
                    status=extraction.get("status", "completed"),
                    degradado=extraction.get("degradado", False),
                    alertas=extraction.get("alertas", []),
                )
                session.add(ext)
                await session.flush()
                for cell in extraction.get("cells", []):
                    session.add(m.ExtractionCell(
                        org_id=review.org_id,
                        extraction_id=ext.id,
                        field=cell["field"],
                        block=cell.get("block", ""),
                        value=cell.get("value"),
                        value_type=cell.get("value_type", "text"),
                        page=cell.get("page"),
                        start_offset=cell.get("start_offset"),
                        end_offset=cell.get("end_offset"),
                        evidence_text=cell.get("evidence_text"),
                        confidence=cell.get("confidence", "low"),
                        needs_human_confirmation=cell.get("needs_human_confirmation", False),
                        flags=cell.get("flags", []),
                    ))

    async def get_extraction(self, review_id: str, record_id: str) -> dict | None:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return None
            record = (await session.execute(
                select(m.Record).where(
                    m.Record.review_id == review.id, m.Record.external_id == record_id,
                )
            )).scalar_one_or_none()
            if record is None:
                return None
            doc = (await session.execute(
                select(m.Document).where(
                    m.Document.review_id == review.id, m.Document.record_id == record.id,
                )
            )).scalar_one_or_none()
            if doc is None:
                return None
            ext = (await session.execute(
                select(m.Extraction).where(
                    m.Extraction.review_id == review.id, m.Extraction.document_id == doc.id,
                )
            )).scalar_one_or_none()
            if ext is None:
                return None
            cells = (await session.execute(
                select(m.ExtractionCell).where(m.ExtractionCell.extraction_id == ext.id)
            )).scalars().all()
            return {
                "record_id": record_id,
                "schema_version": ext.schema_version,
                "status": ext.status,
                "degradado": ext.degradado,
                "alertas": ext.alertas,
                "cells": [
                    {
                        "field": c.field, "block": c.block, "value": c.value,
                        "value_type": c.value_type, "page": c.page,
                        "start_offset": c.start_offset, "end_offset": c.end_offset,
                        "evidence_text": c.evidence_text, "confidence": c.confidence,
                        "needs_human_confirmation": c.needs_human_confirmation, "flags": c.flags,
                    }
                    for c in cells
                ],
            }

    async def get_extractions(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.Extraction).where(m.Extraction.review_id == review.id)
            )).scalars().all()
            record_ids = {r.id: r.external_id for r in (await session.execute(
                select(m.Record).where(m.Record.review_id == review.id)
            )).scalars().all()}
            doc_to_record: dict[uuid.UUID, str] = {}
            docs = (await session.execute(
                select(m.Document).where(m.Document.review_id == review.id)
            )).scalars().all()
            for d in docs:
                doc_to_record[d.id] = record_ids.get(d.record_id, "")
            return [
                {
                    "record_id": doc_to_record.get(e.document_id, ""),
                    "schema_version": e.schema_version,
                    "status": e.status,
                    "degradado": e.degradado,
                    "alertas": e.alertas,
                }
                for e in rows
            ]

    async def add_rob_assessment(self, review_id: str, assessment: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                doc_id = await self._resolve_document_id(session, review, assessment["record_id"])
                session.add(m.RobAssessment(
                    org_id=review.org_id,
                    review_id=review.id,
                    document_id=doc_id,
                    instrument=assessment.get("instrument", "rob2"),
                    overall_judgment=assessment.get("overall_judgment", "high"),
                    domain_results=assessment.get("domain_results", []),
                    degradado=assessment.get("degradado", False),
                    alertas=assessment.get("alertas", []),
                ))

    async def get_rob_assessments(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.RobAssessment).where(m.RobAssessment.review_id == review.id)
            )).scalars().all()
            record_ids = {r.id: r.external_id for r in (await session.execute(
                select(m.Record).where(m.Record.review_id == review.id)
            )).scalars().all()}
            doc_to_record: dict[uuid.UUID, str] = {}
            docs = (await session.execute(
                select(m.Document).where(m.Document.review_id == review.id)
            )).scalars().all()
            for d in docs:
                doc_to_record[d.id] = record_ids.get(d.record_id, "")
            return [
                {
                    "record_id": doc_to_record.get(r.document_id, ""),
                    "instrument": r.instrument,
                    "overall_judgment": r.overall_judgment,
                    "domain_results": r.domain_results,
                    "degradado": r.degradado,
                    "alertas": r.alertas,
                }
                for r in rows
            ]

    async def set_synthesis_config(self, review_id: str, config: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                proto = (await session.execute(
                    select(m.Protocol).where(m.Protocol.review_id == review.id)
                )).scalar_one_or_none()
                if proto is None:
                    raise KeyError(f"Protocol not set for review '{review_id}'")
                proto.synthesis_config = config

    async def get_synthesis_config(self, review_id: str) -> dict | None:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return None
            proto = (await session.execute(
                select(m.Protocol).where(m.Protocol.review_id == review.id)
            )).scalar_one_or_none()
            if proto is None:
                return None
            return proto.synthesis_config

    async def add_synthesis(self, review_id: str, synthesis: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                session.add(m.Synthesis(
                    org_id=review.org_id,
                    review_id=review.id,
                    outcome_key=synthesis["outcome_key"],
                    measure=synthesis.get("measure", ""),
                    model=synthesis.get("model", "random"),
                    k_studies=synthesis.get("k_studies", 0),
                    n_participants=synthesis.get("n_participants"),
                    pooled_effect=synthesis.get("pooled_effect"),
                    se=synthesis.get("se"),
                    ci_low=synthesis.get("ci_low"),
                    ci_high=synthesis.get("ci_high"),
                    z=synthesis.get("z"),
                    p_value=synthesis.get("p_value"),
                    tau2=synthesis.get("tau2"),
                    q=synthesis.get("q"),
                    q_p=synthesis.get("q_p"),
                    i2=synthesis.get("i2"),
                    prediction_low=synthesis.get("prediction_low"),
                    prediction_high=synthesis.get("prediction_high"),
                    egger_intercept=synthesis.get("egger_intercept"),
                    egger_p=synthesis.get("egger_p"),
                    study_effects=synthesis.get("study_effects", []),
                    unmapped=synthesis.get("unmapped", []),
                    status=synthesis.get("status", "draft"),
                    degradado=synthesis.get("degradado", False),
                    alertas=synthesis.get("alertas", []),
                ))

    async def get_synthesis(self, review_id: str, outcome_key: str) -> dict | None:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return None
            row = (await session.execute(
                select(m.Synthesis).where(
                    m.Synthesis.review_id == review.id,
                    m.Synthesis.outcome_key == outcome_key,
                )
            )).scalar_one_or_none()
            if row is None:
                return None
            return self._synthesis_to_dict(row)

    async def get_syntheses(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.Synthesis).where(m.Synthesis.review_id == review.id)
            )).scalars().all()
            return [self._synthesis_to_dict(r) for r in rows]

    async def approve_synthesis(self, review_id: str, outcome_key: str, approved_by: str) -> None:
        from datetime import datetime, timezone

        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                row = (await session.execute(
                    select(m.Synthesis).where(
                        m.Synthesis.review_id == review.id,
                        m.Synthesis.outcome_key == outcome_key,
                    )
                )).scalar_one_or_none()
                if row is None:
                    raise KeyError(f"Synthesis for outcome '{outcome_key}' not found")
                row.status = "approved"
                row.approved_by = approved_by
                row.approved_at = datetime.now(timezone.utc)

    async def add_grade_assessment(self, review_id: str, assessment: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                session.add(m.GradeAssessment(
                    org_id=review.org_id,
                    review_id=review.id,
                    outcome_key=assessment["outcome_key"],
                    starting_certainty=assessment.get("starting_certainty", "high"),
                    domain_results=assessment.get("domain_results", []),
                    final_certainty=assessment.get("final_certainty", "high"),
                    k_studies=assessment.get("k_studies", 0),
                    n_participants=assessment.get("n_participants"),
                    status=assessment.get("status", "draft"),
                    degradado=assessment.get("degradado", False),
                    alertas=assessment.get("alertas", []),
                ))

    async def get_grade_assessments(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.GradeAssessment).where(m.GradeAssessment.review_id == review.id)
            )).scalars().all()
            return [
                {
                    "outcome_key": g.outcome_key,
                    "starting_certainty": g.starting_certainty,
                    "domain_results": g.domain_results,
                    "final_certainty": g.final_certainty,
                    "k_studies": g.k_studies,
                    "n_participants": g.n_participants,
                    "status": g.status,
                    "approved_by": g.approved_by,
                    "approved_at": g.approved_at.isoformat() if g.approved_at else None,
                    "degradado": g.degradado,
                    "alertas": g.alertas,
                }
                for g in rows
            ]

    async def approve_grade(self, review_id: str, outcome_key: str, approved_by: str) -> None:
        from datetime import datetime, timezone

        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                row = (await session.execute(
                    select(m.GradeAssessment).where(
                        m.GradeAssessment.review_id == review.id,
                        m.GradeAssessment.outcome_key == outcome_key,
                    )
                )).scalar_one_or_none()
                if row is None:
                    raise KeyError(f"GRADE assessment for outcome '{outcome_key}' not found")
                row.status = "approved"
                row.approved_by = approved_by
                row.approved_at = datetime.now(timezone.utc)

    async def add_import_run(self, review_id: str, run: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                session.add(m.ImportRun(
                    org_id=review.org_id,
                    review_id=review.id,
                    source=run.get("source", ""),
                    query=run.get("query"),
                    filename=run.get("filename"),
                    total_found=run.get("total_found", 0),
                    imported=run.get("imported", 0),
                    duplicates=run.get("duplicates", 0),
                ))

    async def get_import_runs(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.ImportRun).where(m.ImportRun.review_id == review.id)
            )).scalars().all()
            return [
                {
                    "source": r.source, "query": r.query, "filename": r.filename,
                    "total_found": r.total_found, "imported": r.imported,
                    "duplicates": r.duplicates, "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]

    async def add_report(self, review_id: str, report: dict) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                kind = report.get("kind", "prisma")
                existing = (await session.execute(
                    select(m.Report).where(m.Report.review_id == review.id, m.Report.kind == kind)
                )).scalar_one_or_none()
                if existing is not None:
                    existing.status = report.get("status", "draft")
                    existing.flow_counts = report.get("flow_counts")
                    existing.discrepancies = report.get("discrepancies", [])
                    existing.checklist = report.get("checklist")
                    existing.sections = report.get("sections", [])
                    existing.artifacts = report.get("artifacts")
                    existing.degradado = report.get("degradado", False)
                    existing.alertas = report.get("alertas", [])
                else:
                    session.add(m.Report(
                        org_id=review.org_id,
                        review_id=review.id,
                        kind=kind,
                        status=report.get("status", "draft"),
                        flow_counts=report.get("flow_counts"),
                        discrepancies=report.get("discrepancies", []),
                        checklist=report.get("checklist"),
                        sections=report.get("sections", []),
                        artifacts=report.get("artifacts"),
                        degradado=report.get("degradado", False),
                        alertas=report.get("alertas", []),
                    ))

    async def get_report(self, review_id: str, kind: str = "prisma") -> dict | None:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return None
            row = (await session.execute(
                select(m.Report).where(m.Report.review_id == review.id, m.Report.kind == kind)
            )).scalar_one_or_none()
            if row is None:
                return None
            return {
                "kind": row.kind, "status": row.status,
                "flow_counts": row.flow_counts, "discrepancies": row.discrepancies,
                "checklist": row.checklist, "sections": row.sections,
                "artifacts": row.artifacts, "approved_by": row.approved_by,
                "approved_at": row.approved_at.isoformat() if row.approved_at else None,
                "degradado": row.degradado, "alertas": row.alertas,
            }

    async def approve_report(self, review_id: str, kind: str, approved_by: str) -> None:
        from datetime import datetime, timezone

        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                row = (await session.execute(
                    select(m.Report).where(m.Report.review_id == review.id, m.Report.kind == kind)
                )).scalar_one_or_none()
                if row is None:
                    raise KeyError(f"Report kind '{kind}' not found for review '{review_id}'")
                row.status = "approved"
                row.approved_by = approved_by
                row.approved_at = datetime.now(timezone.utc)

    async def enable_living(self, review_id: str, cron_expr: str) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                review.living_enabled = True
                review.living_cron = cron_expr

    async def disable_living(self, review_id: str) -> None:
        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                review.living_enabled = False

    async def add_living_update(self, review_id: str, update: dict) -> None:
        from datetime import datetime, timezone

        async with self._sf() as session:
            async with session.begin():
                review = await self._get_review_or_raise(session, review_id)
                session.add(m.LivingUpdate(
                    org_id=review.org_id,
                    review_id=review.id,
                    trigger=update.get("trigger", "manual"),
                    search_sources=update.get("search_sources", []),
                    new_found=update.get("new_found", 0),
                    new_imported=update.get("new_imported", 0),
                    new_duplicates=update.get("new_duplicates", 0),
                    screening_status=update.get("screening_status", "pending"),
                    impact_status=update.get("impact_status", "pending"),
                    impact_result=update.get("impact_result"),
                    notified=update.get("notified", False),
                ))
                review.living_last_run_at = datetime.now(timezone.utc)

    async def get_living_updates(self, review_id: str) -> list[dict]:
        async with self._sf() as session:
            review = (await session.execute(
                select(m.Review).where(m.Review.slug == review_id)
            )).scalar_one_or_none()
            if review is None:
                return []
            rows = (await session.execute(
                select(m.LivingUpdate).where(m.LivingUpdate.review_id == review.id)
            )).scalars().all()
            return [
                {
                    "trigger": u.trigger,
                    "search_sources": u.search_sources,
                    "new_found": u.new_found,
                    "new_imported": u.new_imported,
                    "new_duplicates": u.new_duplicates,
                    "screening_status": u.screening_status,
                    "impact_status": u.impact_status,
                    "impact_result": u.impact_result,
                    "notified": u.notified,
                    "created_at": u.created_at.isoformat(),
                }
                for u in rows
            ]

    async def get_living_reviews(self) -> list[dict]:
        async with self._sf() as session:
            rows = (await session.execute(
                select(m.Review).where(m.Review.living_enabled.is_(True))
            )).scalars().all()
            return [
                {
                    "id": r.slug,
                    "living_cron": r.living_cron,
                    "living_last_run_at": r.living_last_run_at.isoformat() if r.living_last_run_at else None,
                }
                for r in rows
            ]

    async def list_reviews(self) -> list[dict]:
        async with self._sf() as session:
            rows = (await session.execute(
                select(m.Review).order_by(m.Review.created_at.desc())
            )).scalars().all()
            return [
                {
                    "id": r.slug,
                    "created_at": r.created_at.isoformat(),
                    "living_enabled": r.living_enabled,
                    "living_cron": r.living_cron,
                }
                for r in rows
            ]

    @staticmethod
    def _synthesis_to_dict(row: m.Synthesis) -> dict:
        return {
            "outcome_key": row.outcome_key,
            "measure": row.measure,
            "model": row.model,
            "k_studies": row.k_studies,
            "n_participants": row.n_participants,
            "pooled_effect": row.pooled_effect,
            "se": row.se,
            "ci_low": row.ci_low,
            "ci_high": row.ci_high,
            "z": row.z,
            "p_value": row.p_value,
            "tau2": row.tau2,
            "q": row.q,
            "q_p": row.q_p,
            "i2": row.i2,
            "prediction_low": row.prediction_low,
            "prediction_high": row.prediction_high,
            "egger_intercept": row.egger_intercept,
            "egger_p": row.egger_p,
            "study_effects": row.study_effects,
            "unmapped": row.unmapped,
            "status": row.status,
            "approved_by": row.approved_by,
            "approved_at": row.approved_at.isoformat() if row.approved_at else None,
            "degradado": row.degradado,
            "alertas": row.alertas,
        }
