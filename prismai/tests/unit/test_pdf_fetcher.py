"""Unit tests for connectors/pdf_fetcher.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_fetch_pdf_cascading_unpaywall(tmp_path):
    from prismai.connectors.pdf_fetcher import fetch_pdf

    record = {"id": "rec1", "doi": "10.1234/test", "source": "openalex"}

    with (
        patch("prismai.connectors.pdf_fetcher.fetch_pdf_url", new_callable=AsyncMock, return_value="https://example.com/paper.pdf"),
        patch("prismai.connectors.pdf_fetcher.fetch_pmc_pdf_url", new_callable=AsyncMock, return_value=None),
        patch("prismai.connectors.pdf_fetcher._download_pdf", new_callable=AsyncMock, return_value=True),
    ):
        result = await fetch_pdf(record, str(tmp_path), review_id="rev1")
        assert result["source"] == "unpaywall"
        assert result["path"] is not None


@pytest.mark.asyncio
async def test_fetch_pdf_cascading_pmc_fallback(tmp_path):
    from prismai.connectors.pdf_fetcher import fetch_pdf

    record = {"id": "rec2", "doi": "10.1234/test", "source": "openalex"}

    async def side_download(url, dest, timeout=60):
        return "pmc" in url

    with (
        patch("prismai.connectors.pdf_fetcher.fetch_pdf_url", new_callable=AsyncMock, return_value=None),
        patch("prismai.connectors.pdf_fetcher.fetch_pmc_pdf_url", new_callable=AsyncMock, return_value="https://pmc.example.com/paper.pdf"),
        patch("prismai.connectors.pdf_fetcher._download_pdf", new_callable=AsyncMock, side_effect=side_download),
    ):
        result = await fetch_pdf(record, str(tmp_path), review_id="rev1")
        assert result["source"] == "pmc"


@pytest.mark.asyncio
async def test_fetch_pdf_no_source(tmp_path):
    from prismai.connectors.pdf_fetcher import fetch_pdf

    record = {"id": "rec3", "source": "manual"}

    with (
        patch("prismai.connectors.pdf_fetcher._download_pdf", new_callable=AsyncMock, return_value=False),
    ):
        result = await fetch_pdf(record, str(tmp_path), review_id="rev1")
        assert result["path"] is None
        assert result["error"] is not None
