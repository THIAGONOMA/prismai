from prismai.tools.literal import localizar_trecho_literal

DOCUMENTO = (
    "This quasi-experimental study evaluated the impact of a GPT-based tutoring chatbot "
    "on the academic performance of 120 undergraduate students enrolled in Calculus I."
)


class TestLocalizarTrechoLiteral:
    def test_exact_match(self):
        consulta = "GPT-based tutoring chatbot"
        r = localizar_trecho_literal(DOCUMENTO, consulta)
        assert r["encontrado"] is True
        assert r["parcial"] is False
        assert r["posicao"] >= 0

    def test_partial_match(self):
        consulta = "impact of a GPT-based tutoring chatbot on quantum grading scales"
        r = localizar_trecho_literal(DOCUMENTO, consulta)
        assert r["encontrado"] is True
        assert r["parcial"] is True

    def test_nonexistent_query(self):
        r = localizar_trecho_literal(DOCUMENTO, "deep reinforcement learning agent")
        assert r["encontrado"] is False
        assert r["parcial"] is False
        assert r["trecho"] == ""

    def test_short_nonexistent_no_partial(self):
        r = localizar_trecho_literal(DOCUMENTO, "xyz abc")
        assert r["encontrado"] is False
        assert r["parcial"] is False
