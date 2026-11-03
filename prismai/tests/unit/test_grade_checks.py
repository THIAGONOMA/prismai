"""Tests for prismai.checks.grade — deterministic GRADE domain assessments."""
from __future__ import annotations

from prismai.checks.grade import (
    avaliar_imprecisao,
    avaliar_inconsistencia,
    avaliar_risco_vies,
    avaliar_vies_publicacao,
    certeza_final,
)


class TestRiscoVies:
    def test_all_low(self):
        effects = [{"incluido": True, "rob": "low"}] * 5
        rating, _ = avaliar_risco_vies(effects)
        assert rating == 0

    def test_majority_concerns(self):
        effects = [{"incluido": True, "rob": "some_concerns"}] * 4 + [{"incluido": True, "rob": "low"}]
        rating, _ = avaliar_risco_vies(effects)
        assert rating == -1

    def test_majority_high(self):
        effects = [{"incluido": True, "rob": "high"}] * 4 + [{"incluido": True, "rob": "low"}]
        rating, _ = avaliar_risco_vies(effects)
        assert rating == -2

    def test_any_high_minus_1(self):
        effects = [{"incluido": True, "rob": "high"}] + [{"incluido": True, "rob": "low"}] * 5
        rating, _ = avaliar_risco_vies(effects)
        assert rating == -1

    def test_empty(self):
        rating, _ = avaliar_risco_vies([])
        assert rating == 0


class TestInconsistencia:
    def test_low_i2(self):
        rating, _ = avaliar_inconsistencia(20.0, 5)
        assert rating == 0

    def test_moderate_i2(self):
        rating, _ = avaliar_inconsistencia(50.0, 5)
        assert rating == -1

    def test_high_i2(self):
        rating, _ = avaliar_inconsistencia(80.0, 5)
        assert rating == -2

    def test_single_study(self):
        rating, just = avaliar_inconsistencia(0.0, 1)
        assert rating == 0
        assert "1 estudo" in just


class TestImprecisao:
    def test_ci_crosses_null(self):
        rating, _ = avaliar_imprecisao(-0.5, 0.5, "smd", None, 500)
        assert rating == -1

    def test_small_sample(self):
        rating, _ = avaliar_imprecisao(0.1, 0.5, "smd", None, 100)
        assert rating <= -1

    def test_adequate(self):
        rating, _ = avaliar_imprecisao(0.1, 0.5, "smd", None, 500)
        assert rating == 0


class TestViesPublicacao:
    def test_small_k(self):
        rating, just = avaliar_vies_publicacao(0.01, 5)
        assert rating == 0
        assert "não aplicável" in just.lower()

    def test_significant(self):
        rating, _ = avaliar_vies_publicacao(0.05, 15)
        assert rating == -1

    def test_not_significant(self):
        rating, _ = avaliar_vies_publicacao(0.5, 15)
        assert rating == 0


class TestCertezaFinal:
    def test_high_no_downgrade(self):
        assert certeza_final("high", [0, 0, 0, 0, 0]) == "high"

    def test_high_one_downgrade(self):
        assert certeza_final("high", [-1, 0, 0, 0, 0]) == "moderate"

    def test_high_two_downgrade(self):
        assert certeza_final("high", [-1, -1, 0, 0, 0]) == "low"

    def test_high_three_downgrade(self):
        assert certeza_final("high", [-1, -1, -1, 0, 0]) == "very_low"

    def test_low_no_downgrade(self):
        assert certeza_final("low", [0, 0, 0, 0, 0]) == "low"

    def test_low_one_downgrade(self):
        assert certeza_final("low", [-1, 0, 0, 0, 0]) == "very_low"

    def test_clamp_minimum(self):
        assert certeza_final("high", [-2, -2, -2, -2, -2]) == "very_low"
