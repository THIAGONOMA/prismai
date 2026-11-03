"""Unit tests for connectors/openalex.py — normalization and abstract reconstruction."""
from __future__ import annotations

from prismai.connectors.openalex import _normalize, _reconstruct_abstract


class TestReconstructAbstract:
    def test_basic_reconstruction(self):
        inv = {"hello": [0], "world": [1], "foo": [2]}
        assert _reconstruct_abstract(inv) == "hello world foo"

    def test_empty_index(self):
        assert _reconstruct_abstract(None) == ""
        assert _reconstruct_abstract({}) == ""

    def test_out_of_order(self):
        inv = {"c": [2], "a": [0], "b": [1]}
        assert _reconstruct_abstract(inv) == "a b c"

    def test_word_at_multiple_positions(self):
        inv = {"the": [0, 3], "cat": [1], "sat": [2], "mat": [4]}
        assert _reconstruct_abstract(inv) == "the cat sat the mat"


class TestNormalize:
    def test_basic(self):
        work = {
            "id": "W123",
            "doi": "https://doi.org/10.1234/test",
            "title": "My Paper",
            "authorships": [{"author": {"display_name": "Alice"}}],
            "publication_year": 2024,
            "abstract_inverted_index": {"hello": [0], "world": [1]},
        }
        rec = _normalize(work)
        assert rec["id"] == "W123"
        assert rec["doi"] == "10.1234/test"
        assert rec["titulo"] == "My Paper"
        assert rec["abstract"] == "hello world"
        assert rec["authors"] == ["Alice"]
        assert rec["year"] == 2024
        assert rec["source"] == "openalex"

    def test_missing_fields(self):
        work = {"id": "W999"}
        rec = _normalize(work)
        assert rec["titulo"] == ""
        assert rec["abstract"] == ""
        assert rec["doi"] is None
        assert rec["authors"] == []
        assert rec["year"] is None
