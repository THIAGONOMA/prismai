"""Unit tests for connectors/dedup.py — pure-logic fuzzy and DOI deduplication."""
from __future__ import annotations

from prismai.connectors.dedup import _is_fuzzy_dup


class TestFuzzyDup:
    def test_identical_titles_are_duplicates(self):
        assert _is_fuzzy_dup("machine learning for health", ["machine learning for health"])

    def test_very_similar_titles_are_duplicates(self):
        assert _is_fuzzy_dup("machine learning for healthcare", ["machine learning for health care"])

    def test_different_titles_are_not_duplicates(self):
        assert not _is_fuzzy_dup("deep reinforcement learning", ["quantum computing basics"])

    def test_empty_existing_list(self):
        assert not _is_fuzzy_dup("some title", [])

    def test_short_title_close_match(self):
        assert _is_fuzzy_dup("ai in medicine", ["ai in medicin"])

    def test_long_divergent_titles(self):
        a = "a systematic review of interventions for reducing cardiovascular risk"
        b = "neural network architectures for natural language processing tasks"
        assert not _is_fuzzy_dup(a, [b])
