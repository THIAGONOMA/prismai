"""Unit tests for tools/literal.py — document-level search with anchors."""
from __future__ import annotations

from prismai.tools.literal import localizar_trecho_em_documento

_SECTIONS = [
    {"title": "Introduction", "page": 1, "start": 0, "text": "This study investigates the effects of cognitive behavioral therapy on depression outcomes."},
    {"title": "Methods", "page": 3, "start": 100, "text": "We conducted a randomized controlled trial with 200 participants assigned to CBT or waitlist."},
    {"title": "Results", "page": 5, "start": 250, "text": "HAM-D scores decreased significantly in the CBT group compared to control."},
]


def test_exact_match_found():
    result = localizar_trecho_em_documento(_SECTIONS, "randomized controlled trial")
    assert result["encontrado"] is True
    assert result["parcial"] is False
    assert result["pagina"] == 3
    assert result["start_offset"] >= 100
    assert "secao" in result


def test_partial_match():
    result = localizar_trecho_em_documento(
        _SECTIONS,
        "effects of cognitive behavioral therapy on depression outcomes in adults",
    )
    assert result["encontrado"] is True
    assert result["parcial"] is True


def test_not_found():
    result = localizar_trecho_em_documento(_SECTIONS, "quantum computing algorithms")
    assert result["encontrado"] is False
    assert result["parcial"] is False
