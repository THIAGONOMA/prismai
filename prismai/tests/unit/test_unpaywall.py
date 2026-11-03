"""Unit tests for connectors/unpaywall.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_fetch_pdf_url_success():
    from prismai.connectors.unpaywall import fetch_pdf_url

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "best_oa_location": {"url_for_pdf": "https://example.com/paper.pdf"},
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    with patch("prismai.connectors.unpaywall.httpx.AsyncClient") as MockClass:
        MockClass.return_value.__aenter__.return_value = mock_client
        MockClass.return_value.__aexit__.return_value = False

        result = await fetch_pdf_url("10.1234/test")
        assert result == "https://example.com/paper.pdf"


@pytest.mark.asyncio
async def test_fetch_pdf_url_not_found():
    from prismai.connectors.unpaywall import fetch_pdf_url

    mock_resp = MagicMock()
    mock_resp.status_code = 404

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    with patch("prismai.connectors.unpaywall.httpx.AsyncClient") as MockClass:
        MockClass.return_value.__aenter__.return_value = mock_client
        MockClass.return_value.__aexit__.return_value = False

        result = await fetch_pdf_url("10.1234/missing")
        assert result is None
