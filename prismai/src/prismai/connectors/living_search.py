"""Incremental search for living reviews — re-runs original queries and deduplicates."""
from __future__ import annotations

import logging

from prismai.connectors.dedup import _is_fuzzy_dup
from prismai.text.normalize import normalizar

logger = logging.getLogger(__name__)


async def rebuscar_incrementalmente(
    repo,
    review_id: str,
    *,
    max_results: int = 200,
) -> dict:
    """Re-run original search queries and return only genuinely new records.

    Returns: {new_found, new_imported, new_duplicates, new_record_ids, search_sources}
    """
    import_runs = await repo.get_import_runs(review_id)
    existing_records = await repo.get_records(review_id)

    existing_dois: set[str] = set()
    existing_titles: list[str] = []
    for rec in existing_records:
        doi = (rec.get("doi") or "").strip().lower()
        if doi:
            existing_dois.add(doi)
        titulo = rec.get("titulo", "")
        tnorm = normalizar(titulo) if titulo else ""
        if tnorm:
            existing_titles.append(tnorm)

    queries: list[dict] = []
    seen_queries: set[str] = set()
    for run in import_runs:
        source = run.get("source", "")
        query = run.get("query", "")
        if not query or source not in ("openalex", "crossref"):
            continue
        key = f"{source}:{query}"
        if key in seen_queries:
            continue
        seen_queries.add(key)
        queries.append({"source": source, "query": query})

    all_found: list[dict] = []
    search_sources: list[str] = []

    for q in queries:
        try:
            if q["source"] == "openalex":
                from prismai.connectors.openalex import buscar_openalex

                results = await buscar_openalex(q["query"], max_results=max_results)
            else:
                from prismai.connectors.crossref import buscar_crossref

                results = await buscar_crossref(q["query"], max_results=max_results)
            all_found.extend(results)
            search_sources.append(q["source"])
        except Exception as e:
            logger.warning("Living search failed for %s/%s: %s", q["source"], q["query"], e)

    new_records: list[dict] = []
    n_dups = 0
    seen_dois = set(existing_dois)
    seen_titles = list(existing_titles)

    for rec in all_found:
        doi = (rec.get("doi") or "").strip().lower() or None
        titulo = rec.get("titulo", "")
        tnorm = normalizar(titulo) if titulo else ""

        if doi and doi in seen_dois:
            n_dups += 1
            continue
        if tnorm and _is_fuzzy_dup(tnorm, seen_titles):
            n_dups += 1
            continue

        new_records.append(rec)
        if doi:
            seen_dois.add(doi)
        if tnorm:
            seen_titles.append(tnorm)

    new_record_ids: list[str] = []
    if new_records:
        await repo.add_records(review_id, new_records)
        new_record_ids = [r["id"] for r in new_records]
        await repo.add_import_run(review_id, {
            "source": "living_update",
            "query": "; ".join(q["query"] for q in queries),
            "total_found": len(all_found),
            "imported": len(new_records),
            "duplicates": n_dups,
        })

    return {
        "new_found": len(all_found),
        "new_imported": len(new_records),
        "new_duplicates": n_dups,
        "new_record_ids": new_record_ids,
        "search_sources": search_sources,
    }
