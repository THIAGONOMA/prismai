"""Integration tests for the GRADE assessment pipeline (M6)."""
from __future__ import annotations

import json

from prismai.graphs.grade import assess_grade


class FakeLLMGrade:
    """Returns indirectness rating of 0 (no downgrade)."""
    def invoke(self, prompt):
        class Resp:
            content = json.dumps({"rating": 0, "justificativa": "População e intervenção compatíveis"})
        return Resp()


class TestGradePipeline:
    def test_high_certainty_no_issues(self):
        syntheses = [{
            "outcome_key": "pain",
            "measure": "smd",
            "k_studies": 5,
            "i2": 10.0,
            "ci_low": 0.2,
            "ci_high": 0.8,
            "egger_p": None,
            "study_effects": [
                {"incluido": True, "rob": "low", "n_total": 100},
                {"incluido": True, "rob": "low", "n_total": 100},
                {"incluido": True, "rob": "low", "n_total": 100},
                {"incluido": True, "rob": "low", "n_total": 100},
                {"incluido": True, "rob": "low", "n_total": 100},
            ],
        }]
        protocolo = {"P": "Adults", "I": "Drug A", "C": "Placebo", "O": "Pain"}
        envelopes, metricas = assess_grade(syntheses, [], protocolo, FakeLLMGrade())
        assert len(envelopes) == 1
        gr = envelopes[0].resultado
        assert gr.final_certainty == "high"

    def test_downgrade_with_high_rob(self):
        syntheses = [{
            "outcome_key": "pain",
            "measure": "smd",
            "k_studies": 4,
            "i2": 10.0,
            "ci_low": 0.2,
            "ci_high": 0.8,
            "egger_p": None,
            "study_effects": [
                {"incluido": True, "rob": "high", "n_total": 100},
                {"incluido": True, "rob": "high", "n_total": 100},
                {"incluido": True, "rob": "high", "n_total": 100},
                {"incluido": True, "rob": "low", "n_total": 100},
            ],
        }]
        envelopes, _ = assess_grade(syntheses, [], {}, FakeLLMGrade())
        gr = envelopes[0].resultado
        assert gr.final_certainty in ("low", "very_low", "moderate")
        rob_domain = next(d for d in gr.domains if d.domain == "risk_of_bias")
        assert rob_domain.rating < 0
