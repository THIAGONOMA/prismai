"""Lightweight BM25-style section retrieval for long documents."""
from __future__ import annotations

import math
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _idf(term: str, doc_freqs: dict[str, int], n_docs: int) -> float:
    df = doc_freqs.get(term, 0)
    if df == 0:
        return 0.0
    return math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)


def buscar_secoes_relevantes(
    sections: list[dict],
    query: str,
    top_k: int = 3,
) -> list[dict]:
    """BM25-inspired ranking over document sections.

    Returns top_k sections sorted by relevance score (descending).
    Each section dict must have at least a "text" key.
    """
    if not sections:
        return []

    k1 = 1.5
    b = 0.75

    query_tokens = _tokenize(query)
    if not query_tokens:
        return sections[:top_k]

    section_tokens = [_tokenize(s.get("text", "")) for s in sections]
    n_docs = len(sections)
    avg_dl = sum(len(t) for t in section_tokens) / max(n_docs, 1)

    doc_freqs: dict[str, int] = {}
    for tokens in section_tokens:
        seen = set(tokens)
        for t in seen:
            doc_freqs[t] = doc_freqs.get(t, 0) + 1

    scores: list[tuple[float, int]] = []
    for idx, tokens in enumerate(section_tokens):
        tf_map = Counter(tokens)
        dl = len(tokens)
        score = 0.0
        for qt in query_tokens:
            tf = tf_map.get(qt, 0)
            idf_val = _idf(qt, doc_freqs, n_docs)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * dl / max(avg_dl, 1))
            score += idf_val * numerator / denominator
        scores.append((score, idx))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [sections[idx] for _, idx in scores[:top_k]]
