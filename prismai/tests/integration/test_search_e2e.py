"""Integration test: real call to OpenAlex with a small query."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


@pytest.mark.asyncio
async def test_openalex_returns_records():
    from prismai.connectors.openalex import buscar_openalex

    results = await buscar_openalex("PRISMA systematic review", max_results=5)
    assert isinstance(results, list)
    assert len(results) <= 5
    if results:
        rec = results[0]
        assert "titulo" in rec
        assert "source" in rec
        assert rec["source"] == "openalex"


@pytest.mark.asyncio
async def test_crossref_returns_records():
    from prismai.connectors.crossref import buscar_crossref

    results = await buscar_crossref("PRISMA systematic review", max_results=5)
    assert isinstance(results, list)
    assert len(results) <= 5
    if results:
        rec = results[0]
        assert "titulo" in rec
        assert rec["source"] == "crossref"
