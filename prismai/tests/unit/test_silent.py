from prismai.checks.silent import verificar_calibracao, verificar_escopo
from prismai.core.models import ScreeningResult


def _sr(decision="include", reasons=None, evidence=None, confidence="high"):
    return ScreeningResult(
        decision=decision,
        reasons=reasons or [],
        evidence=evidence or [],
        confidence=confidence,
    )


class TestVerificarEscopo:
    def test_related_terms(self):
        reg = {"titulo": "LLM Tutoring Study", "abstract": "undergraduate students calculus performance"}
        sr = _sr(reasons=["undergraduate students use LLM"], evidence=["calculus performance"])
        r = verificar_escopo(sr, reg)
        assert r["escopo_ok"] is True

    def test_unrelated_terms(self):
        reg = {"titulo": "LLM Tutoring Study", "abstract": "undergraduate students calculus performance"}
        sr = _sr(reasons=["bananas tropicais exportadas"], evidence=["mercado financeiro global"])
        r = verificar_escopo(sr, reg)
        assert r["escopo_ok"] is False


class TestVerificarCalibracao:
    def test_high_confidence_no_evidence(self):
        sr = _sr(confidence="high", evidence=[])
        r = verificar_calibracao(sr, ev_fiel_score=None)
        assert r["calibrado"] is False

    def test_high_confidence_good_evidence(self):
        sr = _sr(confidence="high", evidence=["some evidence"])
        r = verificar_calibracao(sr, ev_fiel_score=1.0)
        assert r["calibrado"] is True

    def test_low_confidence_with_good_evidence(self):
        sr = _sr(confidence="low", evidence=["some evidence"])
        r = verificar_calibracao(sr, ev_fiel_score=1.0)
        assert r["calibrado"] is False
