"""Cascading PDF fetcher: Unpaywall -> PMC -> arXiv -> DOI resolver."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

from prismai.connectors.pmc import fetch_pmc_pdf_url
from prismai.connectors.unpaywall import fetch_pdf_url

logger = logging.getLogger(__name__)


def _arxiv_pdf_url(record: dict) -> str | None:
    """Build arXiv PDF URL from record source/id."""
    source = record.get("source", "")
    ext_id = record.get("id", "")
    if source == "arxiv" or "arxiv.org" in ext_id:
        arxiv_id = ext_id.replace("http://arxiv.org/abs/", "").replace("https://arxiv.org/abs/", "")
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return None


def _doi_resolver_url(doi: str) -> str:
    return f"https://doi.org/{doi}"


async def _download_pdf(url: str, dest: str, timeout: int = 60) -> bool:
    """Download a PDF from URL to dest path. Returns True on success."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return False
            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type and not resp.content[:5] == b"%PDF-":
                return False
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            Path(dest).write_bytes(resp.content)
            return True
        except Exception as e:
            logger.warning("Download failed from %s: %s", url, e)
            return False


async def fetch_pdf(
    record: dict,
    storage_path: str,
    review_id: str = "default",
    timeout: int = 60,
) -> dict:
    """Cascade: Unpaywall -> PMC -> arXiv -> DOI resolver.

    Returns {"path": ..., "source": ..., "error": ...}.
    """
    record_id = record.get("id", "unknown")
    dest = os.path.join(storage_path, review_id, f"{record_id}.pdf")
    doi = record.get("doi")

    sources: list[tuple[str, str | None]] = []

    if doi:
        pdf_url = await fetch_pdf_url(doi)
        if pdf_url:
            sources.append(("unpaywall", pdf_url))

        pmc_url = await fetch_pmc_pdf_url(doi)
        if pmc_url:
            sources.append(("pmc", pmc_url))

    arxiv_url = _arxiv_pdf_url(record)
    if arxiv_url:
        sources.append(("arxiv", arxiv_url))

    if doi:
        sources.append(("doi", _doi_resolver_url(doi)))

    for source_name, url in sources:
        if url and await _download_pdf(url, dest, timeout):
            return {"path": dest, "source": source_name, "error": None}

    return {"path": None, "source": None, "error": f"No PDF found for record {record_id}"}
