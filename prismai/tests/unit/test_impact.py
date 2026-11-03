"""Unit tests for impact detector."""
from __future__ import annotations

from prismai.checks.impact import detectar_impacto


class TestImpactDetector:
    def test_no_change(self):
        antes = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.01, "i2": 30.0}]
        depois = [{"outcome_key": "pain", "pooled_effect": 0.55, "p_value": 0.008, "i2": 32.0}]
        result = detectar_impacto(antes, depois)
        assert not result.impacto
        assert len(result.detalhes) == 0

    def test_direction_change(self):
        antes = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.01, "i2": 30.0}]
        depois = [{"outcome_key": "pain", "pooled_effect": -0.3, "p_value": 0.04, "i2": 35.0}]
        result = detectar_impacto(antes, depois)
        assert result.impacto
        assert any(d.tipo == "mudanca_direcao" for d in result.detalhes)

    def test_significance_change(self):
        antes = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.04, "i2": 30.0}]
        depois = [{"outcome_key": "pain", "pooled_effect": 0.45, "p_value": 0.06, "i2": 30.0}]
        result = detectar_impacto(antes, depois)
        assert result.impacto
        assert any(d.tipo == "mudanca_significancia" for d in result.detalhes)

    def test_heterogeneity_change(self):
        antes = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.01, "i2": 20.0}]
        depois = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.01, "i2": 60.0}]
        result = detectar_impacto(antes, depois)
        assert result.impacto
        assert any(d.tipo == "mudanca_heterogeneidade" for d in result.detalhes)

    def test_grade_certainty_change(self):
        antes = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.01, "i2": 30.0}]
        depois = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.01, "i2": 30.0}]
        grade_a = [{"outcome_key": "pain", "final_certainty": "high"}]
        grade_d = [{"outcome_key": "pain", "final_certainty": "moderate"}]
        result = detectar_impacto(antes, depois, grade_a, grade_d)
        assert result.impacto
        assert any(d.tipo == "mudanca_certeza" for d in result.detalhes)

    def test_new_outcome(self):
        antes = []
        depois = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.01}]
        result = detectar_impacto(antes, depois)
        assert result.impacto
        assert any(d.tipo == "novo_desfecho" for d in result.detalhes)

    def test_empty_both(self):
        result = detectar_impacto([], [])
        assert not result.impacto

    def test_multiple_impacts(self):
        antes = [{"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.04, "i2": 20.0}]
        depois = [{"outcome_key": "pain", "pooled_effect": -0.3, "p_value": 0.06, "i2": 50.0}]
        result = detectar_impacto(antes, depois)
        assert result.impacto
        assert len(result.detalhes) >= 2
