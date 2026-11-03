from __future__ import annotations

import difflib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prismai.persistence import models_db as m
from prismai.text.normalize import normalizar

FUZZY_THRESHOLD = 0.92


async def deduplicate(
    session: AsyncSession,
    review_id: "m.uuid.UUID",
    candidates: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Split *candidates* into (new, duplicates) against records already in the DB."""
    existing_dois: set[str] = set()
    existing_titles: list[str] = []

    rows = (await session.execute(
        select(m.Record.doi, m.Record.title_norm).where(m.Record.review_id == review_id)
    )).all()

    for doi, tnorm in rows:
        if doi:
            existing_dois.add(doi.lower())
        if tnorm:
            existing_titles.append(tnorm)

    new: list[dict] = []
    dups: list[dict] = []

    seen_dois: set[str] = set(existing_dois)
    seen_titles: list[str] = list(existing_titles)

    for rec in candidates:
        doi = (rec.get("doi") or "").strip().lower() or None
        titulo = rec.get("titulo", "")
        tnorm = normalizar(titulo) if titulo else ""

        if doi and doi in seen_dois:
            dups.append(rec)
            continue

        if tnorm and _is_fuzzy_dup(tnorm, seen_titles):
            dups.append(rec)
            continue

        new.append(rec)
        if doi:
            seen_dois.add(doi)
        if tnorm:
            seen_titles.append(tnorm)

    return new, dups


def _is_fuzzy_dup(title_norm: str, existing: list[str]) -> bool:
    for ex in existing:
        ratio = difflib.SequenceMatcher(None, title_norm, ex).ratio()
        if ratio >= FUZZY_THRESHOLD:
            return True
    return False
