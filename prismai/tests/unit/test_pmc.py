"""Unit tests for connectors/pmc.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_fetch_pmc_pdf_url_success():
    from prismai.connectors.pmc import fetch_pmc_pdf_url

    xml_response = (
        '<OA><records><record>'
        '<link format="pdf" href="https://pmc.ncbi.nlm.nih.gov/papers/PMC123.pdf"/>'
        '</record></records></OA>'
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = xml_response

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    with patch("prismai.connectors.pmc.httpx.AsyncClient") as MockClass:
        MockClass.return_value.__aenter__.return_value = mock_client
        MockClass.return_value.__aexit__.return_value = False

        result = await fetch_pmc_pdf_url("10.1234/test")
        assert result is not None
        assert "PMC123.pdf" in result


@pytest.mark.asyncio
async def test_fetch_pmc_pdf_url_no_result():
    from prismai.connectors.pmc import fetch_pmc_pdf_url

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<OA><records></records></OA>"

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    with patch("prismai.connectors.pmc.httpx.AsyncClient") as MockClass:
        MockClass.return_value.__aenter__.return_value = mock_client
        MockClass.return_value.__aexit__.return_value = False

        result = await fetch_pmc_pdf_url("10.1234/missing")
        assert result is None
