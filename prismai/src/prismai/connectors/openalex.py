"""OpenAlex /works connector with cursor-based pagination."""
from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org/works"
DEFAULT_PER_PAGE = 100
MAX_RETRIES = 3
INITIAL_BACKOFF = 2.0


async def buscar_openalex(
    query: str,
    *,
    max_results: int = 200,
    api_key: str | None = None,
    filters: str | None = None,
) -> list[dict]:
    """Search OpenAlex and return normalized records."""
    params: dict[str, str | int] = {
        "search": query,
        "per_page": min(DEFAULT_PER_PAGE, max_results),
        "cursor": "*",
        "select": "id,doi,title,authorships,publication_year,abstract_inverted_index",
    }
    if api_key:
        params["api_key"] = api_key
    if filters:
        params["filter"] = filters

    results: list[dict] = []

    async with httpx.AsyncClient(timeout=30) as client:
        while len(results) < max_results:
            data = await _fetch_with_retry(client, params)
            if data is None:
                break

            for work in data.get("results", []):
                results.append(_normalize(work))
                if len(results) >= max_results:
                    break

            next_cursor = data.get("meta", {}).get("next_cursor")
            if not next_cursor or not data.get("results"):
                break
            params["cursor"] = next_cursor

    return results


def _normalize(work: dict) -> dict:
    doi_raw = work.get("doi") or ""
    doi = doi_raw.replace("https://doi.org/", "").strip() or None

    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

    authors = [
        a.get("author", {}).get("display_name", "")
        for a in (work.get("authorships") or [])
        if a.get("author", {}).get("display_name")
    ]

    return {
        "id": work.get("id", ""),
        "titulo": work.get("title") or "",
        "abstract": abstract,
        "doi": doi,
        "authors": authors,
        "year": work.get("publication_year"),
        "source": "openalex",
    }


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


async def _fetch_with_retry(client: httpx.AsyncClient, params: dict) -> dict | None:
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(BASE_URL, params=params)
            if resp.status_code == 429:
                wait = INITIAL_BACKOFF * (2 ** attempt)
                logger.warning("OpenAlex rate limit, retrying in %.1fs", wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError:
            logger.exception("OpenAlex HTTP error")
            return None
        except httpx.HTTPError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(INITIAL_BACKOFF * (2 ** attempt))
                continue
            logger.exception("OpenAlex connection error after retries")
            return None
    return None
