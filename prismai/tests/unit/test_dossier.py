"""Unit tests for report/dossier.py — montar_dossie."""
from __future__ import annotations

import pytest

from prismai.persistence.memory import InMemoryRepository
from prismai.report.dossier import montar_dossie


@pytest.mark.asyncio
async def test_montar_dossie_calls_all_methods():
    repo = InMemoryRepository()
    await repo.create_review("rev1")
    await repo.set_protocol("rev1", {"pergunta": "test?"})
    await repo.add_records("rev1", [{"id": "r1"}])
    await repo.add_decision("rev1", {"registro_id": "r1", "decision": "include"})

    dossie = await montar_dossie(repo, "rev1")
    assert "protocol" in dossie
    assert "import_runs" in dossie
    assert "records" in dossie
    assert "decisions" in dossie
    assert "conflicts" in dossie
    assert "documents" in dossie
    assert "eligibility" in dossie
    assert "extractions" in dossie
    assert "rob" in dossie
    assert "syntheses" in dossie
    assert "grade" in dossie
    assert dossie["protocol"]["pergunta"] == "test?"
    assert len(dossie["records"]) == 1


@pytest.mark.asyncio
async def test_montar_dossie_empty_review():
    repo = InMemoryRepository()
    await repo.create_review("rev2")

    dossie = await montar_dossie(repo, "rev2")
    assert dossie["protocol"] is None
    assert dossie["records"] == []
    assert dossie["decisions"] == []
