"""SAQ task definitions for the prismai worker."""
from __future__ import annotations

import asyncio
import logging

from prismai.config import settings
from prismai.graphs.screening import screen_v4
from prismai.llm.client import criar_llm

logger = logging.getLogger(__name__)

BATCH_SIZE = 10


async def run_screening_task(ctx: dict, *, job_id: str, review_id: str, org_id: str, model: str, temperature: float):
    """Screen all pending records for a review. Idempotent: skips already-decided records."""
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    records = await repo.get_records(review_id)
    decided = await repo.get_decided_registro_ids(review_id)
    pending = [r for r in records if r["id"] not in decided]

    if not pending:
        logger.info("No pending records for review %s", review_id)
        await notify_progress(sf, job_id, len(records), len(records), done=True)
        return

    protocol = await repo.get_protocol(review_id)
    if not protocol:
        logger.error("Protocol not set for review %s", review_id)
        return

    llm = criar_llm(model=model, temperature=temperature)
    total = len(records)
    progress = total - len(pending)
    timeout = settings.screening_timeout_s

    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i : i + BATCH_SIZE]
        for rec in batch:
            try:
                resposta, metricas = await asyncio.wait_for(
                    asyncio.to_thread(screen_v4, rec, protocol, llm),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout screening record %s after %ds", rec["id"], timeout)
                resposta_data = {
                    "registro_id": rec["id"],
                    "decision": "uncertain",
                    "confidence": "low",
                    "reasons": ["Timeout durante processamento"],
                    "evidence": [],
                    "degradado": True,
                    "alertas": [f"Timeout após {timeout}s"],
                }
                await repo.add_decision(review_id, resposta_data)
                progress += 1
                continue

            decision_data = {
                "registro_id": rec["id"],
                "decision": resposta.resultado.decision,
                "confidence": resposta.resultado.confidence,
                "reasons": resposta.resultado.reasons,
                "evidence": resposta.resultado.evidence,
                "degradado": resposta.degradado,
                "alertas": resposta.alertas,
            }
            await repo.add_decision(review_id, decision_data)
            await repo.add_trace(review_id, metricas)
            progress += 1

        await notify_progress(sf, job_id, progress, total)

    await notify_progress(sf, job_id, total, total, done=True)


async def run_dual_screening_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
    model: str,
    temperature: float,
    model_b: str,
    model_auditor: str | None = None,
):
    """Dual screening: two models screen independently, conflicts persisted for human review."""
    from prismai.graphs.dual_screening import screen_dual
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    records = await repo.get_records(review_id)
    decided_a = await repo.get_decided_registro_ids(review_id, screener="primary")
    decided_b = await repo.get_decided_registro_ids(review_id, screener="secondary")
    decided = decided_a & decided_b
    pending = [r for r in records if r["id"] not in decided]

    if not pending:
        logger.info("No pending records for dual review %s", review_id)
        await notify_progress(sf, job_id, len(records), len(records), done=True)
        return

    protocol = await repo.get_protocol(review_id)
    if not protocol:
        logger.error("Protocol not set for review %s", review_id)
        return

    llm_a = criar_llm(model=model, temperature=temperature)
    llm_b = criar_llm(model=model_b, temperature=temperature)
    llm_auditor = criar_llm(model=model_auditor) if model_auditor else None

    total = len(records)
    progress = total - len(pending)
    timeout = settings.screening_timeout_s

    n_agree = 0
    n_screened = 0

    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i : i + BATCH_SIZE]
        for rec in batch:
            try:
                resp_a, met_a, resp_b, met_b, conflict = await asyncio.wait_for(
                    screen_dual(rec, protocol, llm_a, llm_b, llm_auditor, llm_auditor),
                    timeout=timeout * 2,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout dual screening record %s", rec["id"])
                for scr in ("primary", "secondary"):
                    await repo.add_decision(review_id, {
                        "registro_id": rec["id"],
                        "decision": "uncertain",
                        "confidence": "low",
                        "reasons": ["Timeout durante processamento"],
                        "evidence": [],
                        "degradado": True,
                        "alertas": [f"Timeout após {timeout * 2}s"],
                    }, screener=scr)
                progress += 1
                n_screened += 1
                continue

            dec_a = {
                "registro_id": rec["id"],
                "decision": resp_a.resultado.decision,
                "confidence": resp_a.resultado.confidence,
                "reasons": resp_a.resultado.reasons,
                "evidence": resp_a.resultado.evidence,
                "degradado": resp_a.degradado,
                "alertas": resp_a.alertas,
            }
            dec_b = {
                "registro_id": rec["id"],
                "decision": resp_b.resultado.decision,
                "confidence": resp_b.resultado.confidence,
                "reasons": resp_b.resultado.reasons,
                "evidence": resp_b.resultado.evidence,
                "degradado": resp_b.degradado,
                "alertas": resp_b.alertas,
            }
            await repo.add_decision(review_id, dec_a, screener="primary")
            await repo.add_decision(review_id, dec_b, screener="secondary")
            await repo.add_trace(review_id, met_a)
            await repo.add_trace(review_id, met_b)

            if conflict:
                await repo.add_conflict(review_id, conflict)
            else:
                n_agree += 1

            progress += 1
            n_screened += 1

            from prismai.eval.stopping import should_stop as _should_stop

            stop_info = _should_stop(n_screened, n_agree)
            if stop_info["should_stop"]:
                logger.info(
                    "Stopping criterion met for review %s: %s", review_id, stop_info,
                )
                await notify_progress(sf, job_id, progress, total, done=True)
                return

        await notify_progress(sf, job_id, progress, total)

    await notify_progress(sf, job_id, total, total, done=True)


async def run_fulltext_fetch_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
):
    """Fetch PDFs and extract text for all included records without a document."""
    from prismai.connectors.grobid import extract_document
    from prismai.connectors.ocr_check import estimate_ocr_confidence
    from prismai.connectors.pdf_fetcher import fetch_pdf
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    decisions = await repo.get_decisions(review_id)
    included_ids = {d["registro_id"] for d in decisions if d["decision"] == "include"}

    records = await repo.get_records(review_id)
    pending = []
    for rec in records:
        if rec["id"] not in included_ids:
            continue
        existing_doc = await repo.get_document(review_id, rec["id"])
        if existing_doc is not None:
            continue
        pending.append(rec)

    total = len(pending)
    if not total:
        logger.info("No pending documents for review %s", review_id)
        await notify_progress(sf, job_id, 0, 0, done=True)
        return

    storage = settings.pdf_storage_path
    grobid_url = settings.grobid_url
    grobid_timeout = settings.grobid_timeout_s
    ocr_threshold = settings.ocr_confidence_threshold
    fetch_timeout = settings.fulltext_fetch_timeout_s

    for i, rec in enumerate(pending):
        doc_data: dict = {"record_id": rec["id"], "status": "pending"}

        result = await fetch_pdf(rec, storage, review_id=review_id, timeout=fetch_timeout)
        if not result["path"]:
            doc_data["status"] = "failed"
            doc_data["error"] = result.get("error", "PDF not found")
            await repo.add_document(review_id, doc_data)
            await notify_progress(sf, job_id, i + 1, total)
            continue

        doc_data["storage_path"] = result["path"]
        doc_data["fetch_source"] = result["source"]
        doc_data["status"] = "fetched"

        try:
            extracted = await extract_document(result["path"], grobid_url, grobid_timeout)
            doc_data.update({
                "content_text": extracted["content_text"],
                "sections": extracted["sections"],
                "n_pages": extracted["n_pages"],
                "extraction_method": "grobid",
                "status": "extracted",
            })
        except Exception as e:
            logger.warning("GROBID failed for %s, trying PyMuPDF fallback: %s", rec["id"], e)
            try:
                import fitz

                pdf_doc = fitz.open(result["path"])
                text = "\n\n".join(page.get_text() for page in pdf_doc)
                n_pages = len(pdf_doc)
                pdf_doc.close()
                doc_data.update({
                    "content_text": text,
                    "sections": [],
                    "n_pages": n_pages,
                    "extraction_method": "pymupdf",
                    "status": "extracted",
                })
            except Exception as e2:
                logger.error("PyMuPDF fallback also failed for %s: %s", rec["id"], e2)
                doc_data["status"] = "failed"
                doc_data["error"] = str(e2)
                await repo.add_document(review_id, doc_data)
                await notify_progress(sf, job_id, i + 1, total)
                continue

        ocr_conf = estimate_ocr_confidence(result["path"])
        doc_data["ocr_confidence"] = ocr_conf
        if ocr_conf < ocr_threshold:
            doc_data["status"] = "requires_manual_transcription"

        await repo.add_document(review_id, doc_data)
        await notify_progress(sf, job_id, i + 1, total)

    await notify_progress(sf, job_id, total, total, done=True)


async def run_eligibility_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
):
    """Evaluate eligibility for all extracted documents without a decision."""
    from prismai.graphs.eligibility import evaluate_eligibility
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    docs = await repo.get_documents(review_id, status="extracted")
    existing = await repo.get_eligibility_decisions(review_id)
    decided_record_ids = {d["record_id"] for d in existing}

    pending = [d for d in docs if d.get("record_id") not in decided_record_ids]
    total = len(pending)
    if not total:
        logger.info("No pending eligibility evaluations for review %s", review_id)
        await notify_progress(sf, job_id, 0, 0, done=True)
        return

    protocol = await repo.get_protocol(review_id)
    if not protocol:
        logger.error("Protocol not set for review %s", review_id)
        return

    llm = criar_llm(model=model, temperature=temperature)
    records = await repo.get_records(review_id)
    records_by_id = {r["id"]: r for r in records}

    for i, doc in enumerate(pending):
        record_id = doc.get("record_id", "")
        record = records_by_id.get(record_id, {"id": record_id})

        try:
            resposta, metricas = await asyncio.to_thread(
                evaluate_eligibility, doc, record, protocol, llm
            )
        except Exception as e:
            logger.error("Eligibility evaluation failed for %s: %s", record_id, e)
            await notify_progress(sf, job_id, i + 1, total)
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
        await notify_progress(sf, job_id, i + 1, total)

    await notify_progress(sf, job_id, total, total, done=True)


async def run_extraction_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
):
    """Extract data from documents with eligibility include and no extraction yet."""
    from prismai.core.extraction_schema import carregar_schema
    from prismai.graphs.extraction import extract_data
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    elig_decisions = await repo.get_eligibility_decisions(review_id)
    included_ids = {d["record_id"] for d in elig_decisions if d["decision"] == "include"}

    existing_extractions = await repo.get_extractions(review_id)
    extracted_ids = {e["record_id"] for e in existing_extractions}

    pending_ids = included_ids - extracted_ids
    if not pending_ids:
        logger.info("No pending extractions for review %s", review_id)
        await notify_progress(sf, job_id, 0, 0, done=True)
        return

    schema_raw = await repo.get_extraction_schema(review_id)
    schema = carregar_schema(schema_raw)

    llm = criar_llm(model=model, temperature=temperature)
    docs = await repo.get_documents(review_id, status="extracted")
    pending_docs = [d for d in docs if d.get("record_id") in pending_ids]

    total = len(pending_docs)
    for i, doc in enumerate(pending_docs):
        record_id = doc.get("record_id", "")
        records = await repo.get_records(review_id)
        records_by_id = {r["id"]: r for r in records}
        record = records_by_id.get(record_id, {"id": record_id})

        try:
            resposta, metricas = await asyncio.to_thread(
                extract_data, doc, record, schema.model_dump(), llm,
            )
        except Exception as e:
            logger.error("Extraction failed for %s: %s", record_id, e)
            await notify_progress(sf, job_id, i + 1, total)
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
                    "page": c.evidence.page if c.evidence else None,
                    "start_offset": c.evidence.start if c.evidence else None,
                    "end_offset": c.evidence.end if c.evidence else None,
                    "evidence_text": c.evidence.text if c.evidence else None,
                    "confidence": c.confidence,
                    "needs_human_confirmation": c.needs_human_confirmation,
                    "flags": c.flags,
                }
                for c in resposta.resultado.cells
            ],
        }
        await repo.add_extraction(review_id, extraction_data)
        await repo.add_trace(review_id, metricas)
        await notify_progress(sf, job_id, i + 1, total)

    await notify_progress(sf, job_id, total, total, done=True)


async def run_rob_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
):
    """Assess RoB for documents with completed extraction and no RoB assessment."""
    from prismai.graphs.rob import assess_rob
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    extractions = await repo.get_extractions(review_id)
    extracted_ids = {e["record_id"] for e in extractions if e.get("status") == "completed"}

    existing_rob = await repo.get_rob_assessments(review_id)
    assessed_ids = {r["record_id"] for r in existing_rob}

    pending_ids = extracted_ids - assessed_ids
    if not pending_ids:
        logger.info("No pending RoB assessments for review %s", review_id)
        await notify_progress(sf, job_id, 0, 0, done=True)
        return

    llm = criar_llm(model=model, temperature=temperature)
    docs = await repo.get_documents(review_id, status="extracted")
    pending_docs = [d for d in docs if d.get("record_id") in pending_ids]

    total = len(pending_docs)
    for i, doc in enumerate(pending_docs):
        record_id = doc.get("record_id", "")
        records = await repo.get_records(review_id)
        records_by_id = {r["id"]: r for r in records}
        record = records_by_id.get(record_id, {"id": record_id})

        try:
            resposta, metricas = await asyncio.to_thread(
                assess_rob, doc, record, llm,
            )
        except Exception as e:
            logger.error("RoB assessment failed for %s: %s", record_id, e)
            await notify_progress(sf, job_id, i + 1, total)
            continue

        rob_data = {
            "record_id": record_id,
            "instrument": resposta.resultado.instrument,
            "overall_judgment": resposta.resultado.overall,
            "domain_results": [d.model_dump() for d in resposta.resultado.domains],
            "degradado": resposta.degradado,
            "alertas": resposta.alertas,
        }
        await repo.add_rob_assessment(review_id, rob_data)
        await repo.add_trace(review_id, metricas)
        await notify_progress(sf, job_id, i + 1, total)

    await notify_progress(sf, job_id, total, total, done=True)


async def run_synthesis_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
):
    """Synthesize outcomes from config that don't have a synthesis yet."""
    from prismai.core.synthesis_config import carregar_synthesis_config
    from prismai.graphs.synthesis import synthesize
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    config_raw = await repo.get_synthesis_config(review_id)
    config = carregar_synthesis_config(config_raw)
    if config is None:
        logger.error("Synthesis config not set for review %s", review_id)
        await notify_progress(sf, job_id, 0, 0, done=True)
        return

    existing = await repo.get_syntheses(review_id)
    done_keys = {s["outcome_key"] for s in existing}
    pending_outcomes = [oc for oc in config.outcomes if oc.key not in done_keys]

    if not pending_outcomes:
        logger.info("No pending syntheses for review %s", review_id)
        await notify_progress(sf, job_id, 0, 0, done=True)
        return

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
    llm = criar_llm(model=model, temperature=temperature)

    pending_config = {"version": config.version, "outcomes": [oc.model_dump() for oc in pending_outcomes]}

    try:
        envelopes, metricas = await asyncio.to_thread(
            synthesize, pending_config, full_extractions, rob_assessments, protocolo, llm,
        )
    except Exception as e:
        logger.error("Synthesis failed for review %s: %s", review_id, e)
        await notify_progress(sf, job_id, 0, 0, done=True)
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
    await notify_progress(sf, job_id, len(envelopes), len(envelopes), done=True)


async def run_grade_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
):
    """Assess GRADE for outcomes with synthesis but no grade assessment."""
    from prismai.graphs.grade import assess_grade
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    syntheses = await repo.get_syntheses(review_id)
    existing_grade = await repo.get_grade_assessments(review_id)
    graded_keys = {g["outcome_key"] for g in existing_grade}
    pending = [s for s in syntheses if s["outcome_key"] not in graded_keys]

    if not pending:
        logger.info("No pending GRADE assessments for review %s", review_id)
        await notify_progress(sf, job_id, 0, 0, done=True)
        return

    extractions = await repo.get_extractions(review_id)
    protocolo = await repo.get_protocol(review_id) or {}
    llm = criar_llm(model=model, temperature=temperature)

    try:
        envelopes, metricas = await asyncio.to_thread(
            assess_grade, pending, extractions, protocolo, llm,
        )
    except Exception as e:
        logger.error("GRADE assessment failed for review %s: %s", review_id, e)
        await notify_progress(sf, job_id, 0, 0, done=True)
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
    await notify_progress(sf, job_id, len(envelopes), len(envelopes), done=True)


async def run_report_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
):
    """Generate PRISMA 2020 report. Idempotent: skip if report already exists."""
    from prismai.graphs.report import draft_report
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress
    from prismai.report.dossier import montar_dossie
    from prismai.report.flow import contar_fluxo

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    existing = await repo.get_report(review_id, kind="prisma")
    if existing is not None:
        logger.info("Report already exists for review %s, skipping", review_id)
        await notify_progress(sf, job_id, 1, 1, done=True)
        return

    dossie = await montar_dossie(repo, review_id)
    flow = contar_fluxo(dossie)

    llm = criar_llm(model=model, temperature=temperature)

    try:
        resposta, metricas = await asyncio.to_thread(draft_report, dossie, flow, llm)
    except Exception as e:
        logger.error("Report generation failed for review %s: %s", review_id, e)
        await notify_progress(sf, job_id, 0, 0, done=True)
        return

    result = resposta.resultado
    report_data = {
        "kind": "prisma",
        "status": "draft",
        "flow_counts": flow.model_dump(),
        "discrepancies": [d.model_dump() for d in flow.discrepancias],
        "checklist": result.checklist.model_dump(),
        "sections": [s.model_dump() for s in result.sections],
        "degradado": resposta.degradado,
        "alertas": resposta.alertas,
    }
    await repo.add_report(review_id, report_data)
    await repo.add_trace(review_id, metricas)
    await notify_progress(sf, job_id, 1, 1, done=True)


async def run_living_update_task(
    ctx: dict,
    *,
    job_id: str,
    review_id: str,
    org_id: str,
    trigger: str = "manual",
    model: str = "gpt-4o-mini",
    temperature: float = 0,
):
    """Living review update: re-search, screen new records, detect impact."""
    from prismai.checks.impact import detectar_impacto
    from prismai.connectors.living_search import rebuscar_incrementalmente
    from prismai.persistence.postgres import PostgresRepository
    from prismai.queue.helpers import get_session_factory, notify_progress

    sf = get_session_factory()
    repo = PostgresRepository(sf)

    result = await rebuscar_incrementalmente(repo, review_id)

    update_data: dict = {
        "trigger": trigger,
        "search_sources": result["search_sources"],
        "new_found": result["new_found"],
        "new_imported": result["new_imported"],
        "new_duplicates": result["new_duplicates"],
        "screening_status": "pending",
        "impact_status": "none",
        "notified": False,
    }

    if not result["new_record_ids"]:
        update_data["screening_status"] = "completed"
        await repo.add_living_update(review_id, update_data)
        await notify_progress(sf, job_id, 1, 1, done=True)
        return

    update_data["screening_status"] = "running"
    protocol = await repo.get_protocol(review_id)
    if not protocol:
        logger.error("Protocol not set for review %s", review_id)
        update_data["screening_status"] = "completed"
        await repo.add_living_update(review_id, update_data)
        await notify_progress(sf, job_id, 1, 1, done=True)
        return

    llm = criar_llm(model=model, temperature=temperature)
    records = await repo.get_records(review_id)
    new_set = set(result["new_record_ids"])
    new_records = [r for r in records if r["id"] in new_set]
    decided = await repo.get_decided_registro_ids(review_id)
    pending = [r for r in new_records if r["id"] not in decided]

    for rec in pending:
        try:
            resposta, metricas = await asyncio.wait_for(
                asyncio.to_thread(screen_v4, rec, protocol, llm),
                timeout=settings.screening_timeout_s,
            )
        except asyncio.TimeoutError:
            await repo.add_decision(review_id, {
                "registro_id": rec["id"], "decision": "uncertain",
                "confidence": "low", "reasons": ["Timeout"],
                "evidence": [], "degradado": True, "alertas": ["Timeout"],
            })
            continue

        await repo.add_decision(review_id, {
            "registro_id": rec["id"],
            "decision": resposta.resultado.decision,
            "confidence": resposta.resultado.confidence,
            "reasons": resposta.resultado.reasons,
            "evidence": resposta.resultado.evidence,
            "degradado": resposta.degradado,
            "alertas": resposta.alertas,
        })
        await repo.add_trace(review_id, metricas)

    update_data["screening_status"] = "completed"

    syntheses_antes = await repo.get_syntheses(review_id)
    grade_antes = await repo.get_grade_assessments(review_id)

    decisions = await repo.get_decisions(review_id)
    new_includes = [d for d in decisions if d["registro_id"] in new_set and d["decision"] == "include"]

    if new_includes and syntheses_antes:
        update_data["impact_status"] = "running"
        syntheses_depois = await repo.get_syntheses(review_id)
        grade_depois = await repo.get_grade_assessments(review_id)

        impact = detectar_impacto(syntheses_antes, syntheses_depois, grade_antes, grade_depois)
        update_data["impact_status"] = "completed"
        update_data["impact_result"] = impact.model_dump()
        update_data["notified"] = not impact.impacto
    else:
        update_data["impact_status"] = "none" if not new_includes else "pending"

    await repo.add_living_update(review_id, update_data)
    await notify_progress(sf, job_id, 1, 1, done=True)
