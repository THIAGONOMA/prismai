"""Tests for prismai.synthesis.bias — Egger's test and funnel data."""
from __future__ import annotations

from prismai.synthesis.bias import egger_test, funnel_data


class TestEgger:
    def test_too_few_studies(self):
        effects = [{"yi": 0.5, "vi": 0.1}] * 5
        r = egger_test(effects)
        assert r["not_evaluable"] is True

    def test_enough_studies(self):
        effects = [{"yi": 0.3 + 0.05 * i, "vi": 0.1 + 0.01 * i} for i in range(12)]
        r = egger_test(effects)
        assert "intercept" in r
        assert "p" in r

    def test_symmetric_data(self):
        effects = [{"yi": 0.5 + 0.01 * i, "vi": 0.1} for i in range(15)]
        r = egger_test(effects)
        assert "intercept" in r or r.get("not_evaluable")


class TestFunnelData:
    def test_basic(self):
        effects = [{"yi": 0.3, "vi": 0.04, "record_id": "r1"}]
        data = funnel_data(effects, 0.3)
        assert len(data) == 1
        assert abs(data[0]["se"] - 0.2) < 1e-6

    def test_skips_none(self):
        effects = [{"yi": None, "vi": None}, {"yi": 0.5, "vi": 0.1}]
        data = funnel_data(effects, 0.5)
        assert len(data) == 1
