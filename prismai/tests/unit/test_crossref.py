"""Unit tests for connectors/crossref.py — normalization."""
from __future__ import annotations

from prismai.connectors.crossref import _normalize


class TestNormalize:
    def test_basic(self):
        item = {
            "DOI": "10.1234/test",
            "title": ["My Paper Title"],
            "author": [{"family": "Smith", "given": "John"}],
            "published": {"date-parts": [[2023, 6, 15]]},
            "abstract": "This is the abstract.",
        }
        rec = _normalize(item)
        assert rec["doi"] == "10.1234/test"
        assert rec["titulo"] == "My Paper Title"
        assert rec["authors"] == ["Smith, John"]
        assert rec["year"] == 2023
        assert rec["abstract"] == "This is the abstract."
        assert rec["source"] == "crossref"

    def test_missing_fields(self):
        item = {}
        rec = _normalize(item)
        assert rec["doi"] is None
        assert rec["titulo"] == ""
        assert rec["authors"] == []
        assert rec["year"] is None
        assert rec["abstract"] == ""

    def test_multiple_authors(self):
        item = {
            "DOI": "10.5555/xyz",
            "title": ["Test"],
            "author": [
                {"family": "Doe", "given": "Jane"},
                {"family": "Roe", "given": ""},
                {"family": "Moe"},
            ],
        }
        rec = _normalize(item)
        assert rec["authors"] == ["Doe, Jane", "Roe", "Moe"]

    def test_published_online_fallback(self):
        item = {"published-online": {"date-parts": [[2021]]}}
        rec = _normalize(item)
        assert rec["year"] == 2021
