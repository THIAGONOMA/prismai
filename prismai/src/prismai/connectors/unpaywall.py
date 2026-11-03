"""Unpaywall connector: find open-access PDF URLs by DOI."""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.unpaywall.org/v2"


async def fetch_pdf_url(doi: str, email: str = "prismai@example.com") -> str | None:
    """Query Unpaywall for an OA PDF link. Returns URL or None."""
    url = f"{_BASE_URL}/{doi}?email={email}"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            best = data.get("best_oa_location") or {}
            pdf_url = best.get("url_for_pdf") or best.get("url")
            return pdf_url
        except Exception as e:
            logger.warning("Unpaywall lookup failed for %s: %s", doi, e)
            return None
