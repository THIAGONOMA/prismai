"""PMC Open Access connector: find PDF URLs via NCBI OA API."""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_OA_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"


async def fetch_pmc_pdf_url(doi: str) -> str | None:
    """Query PMC OA service for a PDF link by DOI. Returns URL or None."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(_OA_URL, params={"id": f"doi:{doi}", "format": "pdf"})
            if resp.status_code != 200:
                return None
            text = resp.text
            if 'format="pdf"' in text and 'href="' in text:
                start = text.index('href="') + 6
                end = text.index('"', start)
                url = text[start:end]
                if url.startswith("ftp://"):
                    url = url.replace("ftp://", "https://")
                return url
            return None
        except Exception as e:
            logger.warning("PMC lookup failed for %s: %s", doi, e)
            return None
