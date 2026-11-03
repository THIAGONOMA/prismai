"""O julgamento do LLM prevalece sobre a pista heurística, sem rede."""
from prismai.tools.sufficiency import avaliar_suficiencia, pista_heuristica

H04 = {
    "titulo": "A Randomized Trial of an LLM Tutor on Algebra Achievement",
    "abstract": (
        "We randomized 214 undergraduates to an LLM tutor or standard tutoring and "
        "measured algebra achievement with a validated 40-item instrument at baseline and "
        "at twelve weeks. The intervention group scored 8.4 points higher (95% CI 4.1 to "
        "12.7, p = 0.002). Going beyond anecdotal reports of enthusiasm, we quantified "
        "learning gains directly. We draw no conclusions about retention past one term, "
        "which the present design cannot address."
    ),
}


class _Resp:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    def invoke(self, messages, **kwargs):
        self.messages = messages
        return _Resp(self.content)


def test_llm_overrides_negation_trap():
    pista = pista_heuristica(H04)
    assert pista["suficiente"] is False

    fake = FakeLLM(
        '{"suficiente": true, "tipo_insuficiencia": null, "motivo": "ensaio com medicao"}'
    )
    r = avaliar_suficiencia(H04, {}, llm=fake)

    assert r["fonte"] == "llm"
    assert r["confiavel"] is True
    assert r["suficiente"] is True
    assert r["pista_heuristica"]["suficiente"] is False
    texto = " ".join(getattr(m, "content", "") for m in fake.messages)
    assert "nao confiavel" in texto.lower() or "não confiável" in texto.lower() or "nao confiavel" in texto


def test_parse_invalido_cai_na_heuristica():
    fake = FakeLLM("isto nao e json")
    r = avaliar_suficiencia(H04, {}, llm=fake)
    assert r["fonte"] == "heuristica"
    assert r["confiavel"] is False
    assert r["suficiente"] is False
