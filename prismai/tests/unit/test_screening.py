import pytest

from prismai.checks.screening import (
    avaliar,
    decisao_correta,
    desfecho_respeitado,
    evidencia_fiel,
    incerto_coerente,
    motivo_alinhado,
    motivos_presentes,
)
from prismai.core.models import ScreeningResult
from prismai.eval.golden import carregar_casos, carregar_registros


def _sr(decision="include", reasons=None, evidence=None, confidence="high"):
    return ScreeningResult(
        decision=decision,
        reasons=reasons if reasons is not None else ["motivo"],
        evidence=evidence if evidence is not None else [],
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# decisao_correta
# ---------------------------------------------------------------------------
class TestDecisaoCorreta:
    def test_exact_match(self):
        assert decisao_correta(_sr(decision="include"), "include") is True

    def test_mismatch(self):
        assert decisao_correta(_sr(decision="exclude"), "include") is False

    def test_accepted_alternates(self):
        assert decisao_correta(_sr(decision="exclude"), "uncertain", aceitos=["uncertain", "exclude"]) is True


# ---------------------------------------------------------------------------
# evidencia_fiel
# ---------------------------------------------------------------------------
class TestEvidenciaFiel:
    def test_all_present(self):
        reg = {"titulo": "Test", "abstract": "alpha beta gamma delta"}
        sr = _sr(evidence=["alpha beta", "gamma delta"])
        assert evidencia_fiel(sr, reg) == 1.0

    def test_one_missing(self):
        reg = {"titulo": "Test", "abstract": "alpha beta gamma delta"}
        sr = _sr(evidence=["alpha beta", "xpto nao existe"])
        score = evidencia_fiel(sr, reg)
        assert score is not None
        assert score == 0.5

    def test_no_evidence(self):
        reg = {"titulo": "Test", "abstract": "alpha beta"}
        sr = _sr(evidence=[])
        assert evidencia_fiel(sr, reg) is None


# ---------------------------------------------------------------------------
# incerto_coerente
# ---------------------------------------------------------------------------
class TestIncertoCoerente:
    def test_uncertain_low_empty_evidence(self):
        sr = _sr(decision="uncertain", confidence="low", evidence=[])
        assert incerto_coerente(sr) is True

    def test_uncertain_high_returns_false(self):
        sr = _sr(decision="uncertain", confidence="high")
        assert incerto_coerente(sr) is False

    def test_non_uncertain_always_true(self):
        sr = _sr(decision="include", confidence="high")
        assert incerto_coerente(sr) is True


# ---------------------------------------------------------------------------
# motivos_presentes
# ---------------------------------------------------------------------------
class TestMotivosPresentes:
    def test_has_reasons(self):
        assert motivos_presentes(_sr(reasons=["reason1"])) is True

    def test_no_reasons(self):
        assert motivos_presentes(_sr(reasons=[])) is False


# ---------------------------------------------------------------------------
# desfecho_respeitado
# ---------------------------------------------------------------------------
class TestDesfechoRespeitado:
    def test_no_academic_outcome_include(self):
        caso = {"tem_desfecho_academico": False}
        sr = _sr(decision="include")
        assert desfecho_respeitado(sr, caso) is False

    def test_no_academic_outcome_exclude(self):
        caso = {"tem_desfecho_academico": False}
        sr = _sr(decision="exclude")
        assert desfecho_respeitado(sr, caso) is True

    def test_has_outcome(self):
        caso = {"tem_desfecho_academico": True}
        sr = _sr(decision="include")
        assert desfecho_respeitado(sr, caso) is None

    def test_none_outcome(self):
        caso = {"tem_desfecho_academico": None}
        sr = _sr()
        assert desfecho_respeitado(sr, caso) is None


# ---------------------------------------------------------------------------
# motivo_alinhado
# ---------------------------------------------------------------------------
class TestMotivoAlinhado:
    def test_criteria_covered(self):
        sr = _sr(reasons=["populacao nao e graduacao"])
        assert motivo_alinhado(sr, ["população"]) == 1.0

    def test_partial_coverage(self):
        sr = _sr(reasons=["populacao nao e graduacao"])
        assert motivo_alinhado(sr, ["população", "desfecho"]) == 0.5

    def test_no_criteria(self):
        sr = _sr(reasons=["algum motivo"])
        assert motivo_alinhado(sr, None) is None


# ---------------------------------------------------------------------------
# avaliar — golden set T01–T12
# ---------------------------------------------------------------------------
REGISTROS_BY_ID = None
CASOS_BY_ID = None


def _load_golden():
    global REGISTROS_BY_ID, CASOS_BY_ID
    if REGISTROS_BY_ID is None:
        REGISTROS_BY_ID = {r.id: r for r in carregar_registros()}
        CASOS_BY_ID = {c.id: c for c in carregar_casos()}


def _reg_dict(reg):
    return {"titulo": reg.titulo, "abstract": reg.abstract}


def _make_result_for_case(caso_id: str) -> ScreeningResult:
    """Build a ScreeningResult matching expected labels for each golden case."""
    _load_golden()
    caso = CASOS_BY_ID[caso_id]
    reg = REGISTROS_BY_ID[caso.registro_id]

    if caso.verificacao == "manual":
        return ScreeningResult(
            decision="uncertain",
            reasons=["technology not explicitly named as LLM"],
            evidence=["a coding assistant powered by recent AI advances"],
            confidence="low",
        )

    decision = caso.esperado
    abstract = reg.abstract

    if decision == "include":
        words = abstract.split()
        ev_chunk = " ".join(words[:10]) if len(words) >= 10 else abstract
        return ScreeningResult(
            decision="include",
            reasons=["população de graduação", "intervenção baseada em LLM", "desfecho acadêmico mensurado"],
            evidence=[ev_chunk],
            confidence="high",
        )

    if decision == "exclude":
        crit = caso.criterio_violado or []
        reasons = []
        for c in crit:
            if c == "população":
                reasons.append("população não é graduação — profissionais de vendas")
            elif c == "intervenção":
                reasons.append("intervenção não envolve LLM — tutoria humana")
            elif c == "desfecho":
                reasons.append("desfecho não inclui desempenho acadêmico")
            elif c == "desenho":
                reasons.append("desenho não empírico — editorial")
            else:
                reasons.append(f"critério violado: {c}")
        if not reasons:
            reasons = ["excluído por critério"]

        words = abstract.split()
        ev_chunk = " ".join(words[:10]) if len(words) >= 10 else abstract
        return ScreeningResult(
            decision="exclude",
            reasons=reasons,
            evidence=[ev_chunk],
            confidence="high",
        )

    # uncertain — if aceitos includes alternate decisions, use one that passes
    if caso.aceitos:
        chosen = caso.aceitos[0]
        words = abstract.split()
        ev_chunk = " ".join(words[:10]) if len(words) >= 10 else abstract
        return ScreeningResult(
            decision=chosen,
            reasons=["informação insuficiente para decisão definitiva"],
            evidence=[ev_chunk] if ev_chunk.strip() else [],
            confidence="low",
        )
    return ScreeningResult(
        decision="uncertain",
        reasons=["informação insuficiente para decisão"],
        evidence=[],
        confidence="low",
    )


_EXPECTED_LABELS = {
    "T01": True,
    "T02": True,
    "T03": True,
    "T04": True,
    "T05": True,
    "T06": True,
    "T07": True,
    "T08": True,
    "T09": None,
    "T10": True,
    "T11": True,
    "T12": True,
}


class TestAvaliarGoldenSet:
    @pytest.fixture(autouse=True)
    def _load(self):
        _load_golden()

    @pytest.mark.parametrize("caso_id,expected_aprovado", list(_EXPECTED_LABELS.items()))
    def test_golden_case(self, caso_id, expected_aprovado):
        caso = CASOS_BY_ID[caso_id]
        reg = REGISTROS_BY_ID[caso.registro_id]
        resultado = _make_result_for_case(caso_id)
        caso_dict = caso.model_dump()
        reg_dict = _reg_dict(reg)

        r = avaliar(caso_dict, resultado, reg_dict)
        assert r["aprovado"] is expected_aprovado, (
            f"Case {caso_id}: expected aprovado={expected_aprovado}, got {r['aprovado']}. Detail: {r}"
        )
