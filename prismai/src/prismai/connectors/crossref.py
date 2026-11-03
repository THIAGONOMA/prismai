"""Crossref /works connector with cursor-based pagination."""
from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.crossref.org/works"
DEFAULT_ROWS = 100
MAX_RETRIES = 3
INITIAL_BACKOFF = 2.0
USER_AGENT = "prismai/0.1 (mailto:prismai@unicamp.br)"


async def buscar_crossref(
    query: str,
    *,
    max_results: int = 200,
    filters: str | None = None,
) -> list[dict]:
    """Search Crossref and return normalized records."""
    params: dict[str, str | int] = {
        "query.bibliographic": query,
        "rows": min(DEFAULT_ROWS, max_results),
        "cursor": "*",
        "select": "DOI,title,author,published,abstract",
    }
    if filters:
        params["filter"] = filters

    headers = {"User-Agent": USER_AGENT}
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        while len(results) < max_results:
            data = await _fetch_with_retry(client, params)
            if data is None:
                break

            message = data.get("message", {})
            items = message.get("items", [])
            if not items:
                break

            for item in items:
                results.append(_normalize(item))
                if len(results) >= max_results:
                    break

            next_cursor = message.get("next-cursor")
            if not next_cursor:
                break
            params["cursor"] = next_cursor

    return results


def _normalize(item: dict) -> dict:
    doi = (item.get("DOI") or "").strip() or None
    titles = item.get("title") or []
    titulo = titles[0] if titles else ""

    authors = []
    for a in item.get("author") or []:
        family = a.get("family", "")
        given = a.get("given", "")
        if family:
            name = f"{family}, {given}" if given else family
            authors.append(name)

    year = None
    published = item.get("published") or item.get("published-print") or item.get("published-online") or {}
    date_parts = published.get("date-parts") or []
    if date_parts and date_parts[0]:
        try:
            year = int(date_parts[0][0])
        except (IndexError, ValueError, TypeError):
            pass

    return {
        "id": doi or "",
        "titulo": titulo,
        "abstract": item.get("abstract") or "",
        "doi": doi,
        "authors": authors,
        "year": year,
        "source": "crossref",
    }


async def _fetch_with_retry(client: httpx.AsyncClient, params: dict) -> dict | None:
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(BASE_URL, params=params)
            if resp.status_code == 429:
                wait = INITIAL_BACKOFF * (2 ** attempt)
                logger.warning("Crossref rate limit, retrying in %.1fs", wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError:
            logger.exception("Crossref HTTP error")
            return None
        except httpx.HTTPError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
                continue
            logger.exception("Crossref connection error after retries")
            return None
    return None
