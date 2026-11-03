"""Tests for prismai.synthesis.pooling — meta-analytic pooling."""
from __future__ import annotations

from prismai.synthesis.pooling import agrupar


def _make_effects(ys, vs):
    return [{"yi": y, "vi": v} for y, v in zip(ys, vs)]


class TestFixed:
    def test_fixed_single_study(self):
        r = agrupar([{"yi": 0.5, "vi": 0.1}], model="fixed")
        assert r["k"] == 1
        assert abs(r["pooled_effect"] - 0.5) < 1e-6

    def test_fixed_two_studies(self):
        effects = _make_effects([0.5, 0.3], [0.1, 0.1])
        r = agrupar(effects, model="fixed")
        assert abs(r["pooled_effect"] - 0.4) < 1e-6
        assert r["k"] == 2


class TestRandom:
    def test_random_homogeneous(self):
        effects = _make_effects([0.5, 0.5, 0.5], [0.1, 0.1, 0.1])
        r = agrupar(effects, model="random")
        assert r["tau2"] == 0.0
        assert abs(r["i2"]) < 1e-6

    def test_random_heterogeneous(self):
        effects = _make_effects([0.1, 0.5, 1.0, 0.2, 0.8], [0.05, 0.05, 0.05, 0.05, 0.05])
        r = agrupar(effects, model="random")
        assert r["tau2"] > 0
        assert r["i2"] > 0
        assert r["k"] == 5

    def test_tau2_zero_when_q_small(self):
        effects = _make_effects([0.5, 0.51, 0.49], [0.1, 0.1, 0.1])
        r = agrupar(effects, model="random")
        assert r["tau2"] >= 0


class TestEdgeCases:
    def test_empty(self):
        r = agrupar([], model="random")
        assert r["k"] == 0
        assert r["pooled_effect"] is None

    def test_skips_none_yi(self):
        effects = [{"yi": 0.5, "vi": 0.1}, {"yi": None, "vi": 0.1}]
        r = agrupar(effects)
        assert r["k"] == 1

    def test_prediction_interval(self):
        effects = _make_effects([0.1, 0.5, 1.0, 0.2, 0.8], [0.05, 0.05, 0.05, 0.05, 0.05])
        r = agrupar(effects, model="random")
        if r.get("prediction_low") is not None:
            assert r["prediction_low"] < r["pooled_effect"]
            assert r["prediction_high"] > r["pooled_effect"]
