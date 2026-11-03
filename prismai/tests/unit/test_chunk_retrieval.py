"""Unit tests for tools/chunk_retrieval.py."""
from __future__ import annotations

from prismai.tools.chunk_retrieval import buscar_secoes_relevantes

_SECTIONS = [
    {"title": "Introduction", "page": 1, "start": 0, "text": "This study examines cognitive behavioral therapy for depression."},
    {"title": "Methods", "page": 3, "start": 100, "text": "Randomized controlled trial with 150 patients treated with CBT."},
    {"title": "Results", "page": 5, "start": 200, "text": "Significant improvement in HAM-D scores after 12 weeks of treatment."},
    {"title": "Discussion", "page": 8, "start": 300, "text": "Our findings confirm previous meta-analyses on CBT efficacy."},
]


def test_returns_top_k():
    results = buscar_secoes_relevantes(_SECTIONS, "cognitive behavioral therapy", top_k=2)
    assert len(results) == 2


def test_relevance_ranking():
    results = buscar_secoes_relevantes(_SECTIONS, "randomized controlled trial patients", top_k=1)
    assert results[0]["title"] == "Methods"


def test_empty_sections():
    results = buscar_secoes_relevantes([], "anything", top_k=3)
    assert results == []


def test_empty_query():
    results = buscar_secoes_relevantes(_SECTIONS, "", top_k=2)
    assert len(results) == 2
