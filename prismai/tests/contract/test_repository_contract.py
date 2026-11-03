"""Contract tests: the same suite runs against InMemoryRepository and PostgresRepository.

Postgres fixtures require DATABASE_URL_TEST in the environment (or a running local Postgres).
Tests that need Postgres are marked with ``pytest.mark.postgres`` and skipped automatically
when the database is not available.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

from prismai.persistence.memory import InMemoryRepository

postgres_available = bool(os.environ.get("DATABASE_URL_TEST"))


async def _make_postgres_repo():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from prismai.persistence.models_db import Base
    from prismai.persistence.postgres import PostgresRepository

    url = os.environ["DATABASE_URL_TEST"]
    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return PostgresRepository(session_factory), engine


# ---------------------------------------------------------------------------
# Contract test suite — parametrized by repo_type
# ---------------------------------------------------------------------------

class TestRepositoryContract:

    @pytest_asyncio.fixture(params=["memory"] + (["postgres"] if postgres_available else []))
    async def repo(self, request):
        if request.param == "memory":
            yield InMemoryRepository()
        else:
            repo, engine = await _make_postgres_repo()
            yield repo
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_and_get_review(self, repo):
        review = await repo.create_review("rev1")
        assert review["id"] == "rev1"
        assert "created_at" in review
        fetched = await repo.get_review("rev1")
        assert fetched["id"] == "rev1"

    @pytest.mark.asyncio
    async def test_duplicate_create_raises(self, repo):
        await repo.create_review("rev1")
        with pytest.raises(ValueError, match="already exists"):
            await repo.create_review("rev1")

    @pytest.mark.asyncio
    async def test_get_review_nonexistent_returns_none(self, repo):
        assert await repo.get_review("nope") is None

    @pytest.mark.asyncio
    async def test_set_and_get_protocol(self, repo):
        await repo.create_review("rev1")
        proto = {"pergunta": "test?", "P": "p", "I": "i", "C": "c", "O": "o"}
        await repo.set_protocol("rev1", proto)
        fetched = await repo.get_protocol("rev1")
        assert fetched["pergunta"] == "test?"

    @pytest.mark.asyncio
    async def test_protocol_nonexistent_review_raises(self, repo):
        with pytest.raises(KeyError, match="not found"):
            await repo.set_protocol("nope", {})

    @pytest.mark.asyncio
    async def test_get_protocol_not_set_returns_none(self, repo):
        await repo.create_review("rev1")
        assert await repo.get_protocol("rev1") is None

    @pytest.mark.asyncio
    async def test_add_and_get_records(self, repo):
        await repo.create_review("rev1")
        count = await repo.add_records("rev1", [{"id": "r1"}, {"id": "r2"}])
        assert count == 2
        records = await repo.get_records("rev1")
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_records_nonexistent_review_raises(self, repo):
        with pytest.raises(KeyError, match="not found"):
            await repo.add_records("nope", [])

    @pytest.mark.asyncio
    async def test_add_and_get_decisions(self, repo):
        await repo.create_review("rev1")
        await repo.add_decision("rev1", {"decision": "include", "registro_id": "r1"})
        decisions = await repo.get_decisions("rev1")
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "include"

    @pytest.mark.asyncio
    async def test_get_decided_registro_ids(self, repo):
        await repo.create_review("rev1")
        await repo.add_decision("rev1", {"decision": "include", "registro_id": "r1"})
        await repo.add_decision("rev1", {"decision": "exclude", "registro_id": "r2"})
        ids = await repo.get_decided_registro_ids("rev1")
        assert ids == {"r1", "r2"}

    @pytest.mark.asyncio
    async def test_add_and_get_traces(self, repo):
        await repo.create_review("rev1")
        await repo.add_trace("rev1", {"step": "triador", "tokens": 42})
        traces = await repo.get_traces("rev1")
        assert len(traces) == 1
        assert traces[0]["step"] == "triador"

    @pytest.mark.asyncio
    async def test_decisions_nonexistent_review_raises(self, repo):
        with pytest.raises(KeyError, match="not found"):
            await repo.add_decision("nope", {})

    @pytest.mark.asyncio
    async def test_traces_nonexistent_review_raises(self, repo):
        with pytest.raises(KeyError, match="not found"):
            await repo.add_trace("nope", {})

    @pytest.mark.asyncio
    async def test_isolation_between_reviews(self, repo):
        await repo.create_review("rev1")
        await repo.create_review("rev2")
        await repo.add_records("rev1", [{"id": "r1"}])
        await repo.add_records("rev2", [{"id": "r2"}])
        assert len(await repo.get_records("rev1")) == 1
        assert len(await repo.get_records("rev2")) == 1
        r1_records = await repo.get_records("rev1")
        assert r1_records[0]["id"] == "r1"

    # --- M3: multi-screener decisions ---

    @pytest.mark.asyncio
    async def test_add_decision_with_screener(self, repo):
        await repo.create_review("rev1")
        await repo.add_decision("rev1", {"decision": "include", "registro_id": "r1"}, screener="primary")
        await repo.add_decision("rev1", {"decision": "exclude", "registro_id": "r1"}, screener="secondary")
        decisions = await repo.get_decisions("rev1")
        assert len(decisions) == 2

    @pytest.mark.asyncio
    async def test_get_decided_ids_filtered_by_screener(self, repo):
        await repo.create_review("rev1")
        await repo.add_decision("rev1", {"decision": "include", "registro_id": "r1"}, screener="primary")
        await repo.add_decision("rev1", {"decision": "exclude", "registro_id": "r1"}, screener="secondary")
        await repo.add_decision("rev1", {"decision": "include", "registro_id": "r2"}, screener="primary")

        all_ids = await repo.get_decided_registro_ids("rev1")
        assert all_ids == {"r1", "r2"}

        primary_ids = await repo.get_decided_registro_ids("rev1", screener="primary")
        assert primary_ids == {"r1", "r2"}

        secondary_ids = await repo.get_decided_registro_ids("rev1", screener="secondary")
        assert secondary_ids == {"r1"}

    # --- M3: conflict lifecycle ---

    @pytest.mark.asyncio
    async def test_conflict_lifecycle(self, repo):
        await repo.create_review("rev1")
        conflict = {
            "registro_id": "r1",
            "decision_a": "include",
            "decision_b": "exclude",
            "screener_a": "primary",
            "screener_b": "secondary",
            "disagreement_score": 3.0,
            "status": "pending",
        }
        await repo.add_conflict("rev1", conflict)

        pending = await repo.get_conflicts("rev1", status="pending")
        assert len(pending) == 1
        assert pending[0]["registro_id"] == "r1"
        assert pending[0]["disagreement_score"] == 3.0

        await repo.resolve_conflict("rev1", "r1", "include", "Human chose include")

        resolved = await repo.get_conflicts("rev1", status="resolved")
        assert len(resolved) == 1
        assert resolved[0]["resolved_decision"] == "include"

        pending_after = await repo.get_conflicts("rev1", status="pending")
        assert len(pending_after) == 0

    @pytest.mark.asyncio
    async def test_conflicts_ordered_by_score_desc(self, repo):
        await repo.create_review("rev1")
        for rid, score in [("r1", 1.0), ("r2", 3.0), ("r3", 2.0)]:
            await repo.add_conflict("rev1", {
                "registro_id": rid,
                "decision_a": "include", "decision_b": "exclude",
                "screener_a": "primary", "screener_b": "secondary",
                "disagreement_score": score, "status": "pending",
            })
        conflicts = await repo.get_conflicts("rev1")
        scores = [c["disagreement_score"] for c in conflicts]
        assert scores == [3.0, 2.0, 1.0]

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_conflict_raises(self, repo):
        await repo.create_review("rev1")
        with pytest.raises(KeyError, match="not found"):
            await repo.resolve_conflict("rev1", "nope", "include", "note")

    # --- M4: document lifecycle ---

    @pytest.mark.asyncio
    async def test_document_lifecycle(self, repo):
        await repo.create_review("rev1")
        doc = {"record_id": "r1", "status": "pending", "fetch_source": "unpaywall"}
        await repo.add_document("rev1", doc)

        fetched = await repo.get_document("rev1", "r1")
        assert fetched is not None
        assert fetched["status"] == "pending"
        assert fetched["fetch_source"] == "unpaywall"

        await repo.update_document("rev1", "r1", {"status": "extracted", "n_pages": 10})
        updated = await repo.get_document("rev1", "r1")
        assert updated["status"] == "extracted"

    @pytest.mark.asyncio
    async def test_get_documents_filter_by_status(self, repo):
        await repo.create_review("rev1")
        await repo.add_document("rev1", {"record_id": "r1", "status": "pending"})
        await repo.add_document("rev1", {"record_id": "r2", "status": "extracted"})
        all_docs = await repo.get_documents("rev1")
        assert len(all_docs) == 2
        extracted = await repo.get_documents("rev1", status="extracted")
        assert len(extracted) == 1
        assert extracted[0]["record_id"] == "r2"

    @pytest.mark.asyncio
    async def test_get_document_nonexistent_returns_none(self, repo):
        await repo.create_review("rev1")
        assert await repo.get_document("rev1", "nope") is None

    @pytest.mark.asyncio
    async def test_eligibility_decision_lifecycle(self, repo):
        await repo.create_review("rev1")
        elig = {
            "record_id": "r1",
            "decision": "include",
            "confidence": "high",
            "reasons": ["All criteria met"],
        }
        await repo.add_eligibility_decision("rev1", elig)
        decisions = await repo.get_eligibility_decisions("rev1")
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "include"

    # --- M5: extraction lifecycle ---

    @pytest.mark.asyncio
    async def test_extraction_lifecycle(self, repo):
        await repo.create_review("rev1")
        await repo.add_records("rev1", [{"id": "r1"}])
        await repo.add_document("rev1", {
            "record_id": "r1", "status": "extracted", "content_text": "text",
        })
        extraction = {
            "record_id": "r1",
            "schema_version": "cochrane-default-v1",
            "status": "completed",
            "degradado": False,
            "alertas": [],
            "cells": [
                {"field": "n_total", "block": "populacao", "value": 100, "value_type": "integer"},
            ],
        }
        await repo.add_extraction("rev1", extraction)
        fetched = await repo.get_extraction("rev1", "r1")
        assert fetched is not None
        assert fetched["record_id"] == "r1"
        assert fetched["schema_version"] == "cochrane-default-v1"

        all_ext = await repo.get_extractions("rev1")
        assert len(all_ext) == 1

    @pytest.mark.asyncio
    async def test_rob_assessment_lifecycle(self, repo):
        await repo.create_review("rev1")
        await repo.add_records("rev1", [{"id": "r1"}])
        await repo.add_document("rev1", {
            "record_id": "r1", "status": "extracted", "content_text": "text",
        })
        rob = {
            "record_id": "r1",
            "instrument": "rob2",
            "overall_judgment": "low",
            "domain_results": [{"domain": "D1", "judgment": "low"}],
            "degradado": False,
            "alertas": [],
        }
        await repo.add_rob_assessment("rev1", rob)
        all_rob = await repo.get_rob_assessments("rev1")
        assert len(all_rob) == 1
        assert all_rob[0]["overall_judgment"] == "low"

    @pytest.mark.asyncio
    async def test_evidence_span_with_record_id(self, repo):
        await repo.create_review("rev1")
        await repo.add_records("rev1", [{"id": "r1"}])
        await repo.add_document("rev1", {
            "record_id": "r1", "status": "extracted", "content_text": "text",
        })
        span = {
            "record_id": "r1",
            "page": 1,
            "start": 0,
            "end": 10,
            "text": "sample text",
            "criterion": "crit1",
        }
        await repo.add_evidence_span("rev1", span)
        spans = await repo.get_evidence_spans("rev1", record_id="r1")
        assert len(spans) >= 1

    @pytest.mark.asyncio
    async def test_extraction_schema_lifecycle(self, repo):
        await repo.create_review("rev1")
        await repo.set_protocol("rev1", {"pergunta": "test?"})
        schema = {"version": "custom-v1", "fields": []}
        await repo.set_extraction_schema("rev1", schema)
        fetched = await repo.get_extraction_schema("rev1")
        assert fetched is not None
        assert fetched["version"] == "custom-v1"

    # --- M6: synthesis lifecycle ---

    @pytest.mark.asyncio
    async def test_synthesis_lifecycle(self, repo):
        await repo.create_review("rev1")
        await repo.set_protocol("rev1", {"pergunta": "test?"})
        config = {"version": "v1", "outcomes": [{"key": "pain"}]}
        await repo.set_synthesis_config("rev1", config)
        fetched_config = await repo.get_synthesis_config("rev1")
        assert fetched_config is not None
        assert fetched_config["version"] == "v1"

        syn = {
            "outcome_key": "pain",
            "measure": "smd",
            "model": "random",
            "k_studies": 5,
            "pooled_effect": 0.5,
            "se": 0.1,
            "ci_low": 0.3,
            "ci_high": 0.7,
            "study_effects": [],
            "status": "draft",
        }
        await repo.add_synthesis("rev1", syn)
        fetched = await repo.get_synthesis("rev1", "pain")
        assert fetched is not None
        assert fetched["outcome_key"] == "pain"
        assert fetched["pooled_effect"] == 0.5

        all_syn = await repo.get_syntheses("rev1")
        assert len(all_syn) == 1

        await repo.approve_synthesis("rev1", "pain", "reviewer1")
        approved = await repo.get_synthesis("rev1", "pain")
        assert approved["status"] == "approved"
        assert approved["approved_by"] == "reviewer1"

    # --- M7: import run lifecycle ---

    @pytest.mark.asyncio
    async def test_import_run_lifecycle(self, repo):
        await repo.create_review("rev1")
        await repo.add_import_run("rev1", {
            "source": "openalex", "query": "PRISMA",
            "total_found": 100, "imported": 90, "duplicates": 10,
        })
        await repo.add_import_run("rev1", {
            "source": "file", "filename": "refs.ris",
            "total_found": 50, "imported": 45, "duplicates": 5,
        })
        runs = await repo.get_import_runs("rev1")
        assert len(runs) == 2
        assert runs[0]["source"] == "openalex"
        assert runs[1]["total_found"] == 50

    @pytest.mark.asyncio
    async def test_report_lifecycle(self, repo):
        await repo.create_review("rev1")
        report = {
            "kind": "prisma",
            "status": "draft",
            "flow_counts": {"identificados_total": 100},
            "discrepancies": [],
            "checklist": {"version": "prisma-2020"},
            "sections": [{"key": "metodos", "titulo": "Métodos", "corpo": "text"}],
        }
        await repo.add_report("rev1", report)
        fetched = await repo.get_report("rev1", kind="prisma")
        assert fetched is not None
        assert fetched["status"] == "draft"
        assert fetched["flow_counts"]["identificados_total"] == 100

        await repo.approve_report("rev1", "prisma", "reviewer1")
        approved = await repo.get_report("rev1", kind="prisma")
        assert approved["status"] == "approved"
        assert approved["approved_by"] == "reviewer1"

    @pytest.mark.asyncio
    async def test_decisions_include_screener(self, repo):
        await repo.create_review("rev1")
        await repo.add_decision("rev1", {"decision": "include", "registro_id": "r1"}, screener="primary")
        decisions = await repo.get_decisions("rev1")
        assert len(decisions) == 1
        assert "screener" in decisions[0]
        assert decisions[0]["screener"] == "primary"

    @pytest.mark.asyncio
    async def test_living_update_lifecycle(self, repo):
        await repo.create_review("rev_living")
        await repo.enable_living("rev_living", "0 3 * * 1")

        reviews = await repo.get_living_reviews()
        assert any(r["id"] == "rev_living" for r in reviews)

        await repo.add_living_update("rev_living", {
            "trigger": "manual",
            "search_sources": ["openalex"],
            "new_found": 50, "new_imported": 5, "new_duplicates": 45,
            "screening_status": "completed", "impact_status": "none",
            "notified": False,
        })
        updates = await repo.get_living_updates("rev_living")
        assert len(updates) == 1
        assert updates[0]["new_imported"] == 5

        await repo.disable_living("rev_living")
        reviews = await repo.get_living_reviews()
        assert not any(r["id"] == "rev_living" for r in reviews)

    @pytest.mark.asyncio
    async def test_enable_disable_living(self, repo):
        await repo.create_review("rev_toggle")

        reviews = await repo.get_living_reviews()
        assert not any(r["id"] == "rev_toggle" for r in reviews)

        await repo.enable_living("rev_toggle", "0 0 * * *")
        reviews = await repo.get_living_reviews()
        assert any(r["id"] == "rev_toggle" for r in reviews)
        living = next(r for r in reviews if r["id"] == "rev_toggle")
        assert living["living_cron"] == "0 0 * * *"

    @pytest.mark.asyncio
    async def test_grade_lifecycle(self, repo):
        await repo.create_review("rev1")
        grade = {
            "outcome_key": "pain",
            "starting_certainty": "high",
            "domain_results": [{"domain": "risk_of_bias", "rating": -1}],
            "final_certainty": "moderate",
            "k_studies": 5,
            "status": "draft",
        }
        await repo.add_grade_assessment("rev1", grade)
        all_grade = await repo.get_grade_assessments("rev1")
        assert len(all_grade) == 1
        assert all_grade[0]["final_certainty"] == "moderate"

        await repo.approve_grade("rev1", "pain", "reviewer1")
        all_grade2 = await repo.get_grade_assessments("rev1")
        assert all_grade2[0]["status"] == "approved"
