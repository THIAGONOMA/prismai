from prismai.tools.sufficiency import avaliar_suficiencia

PROTOCOLO = {
    "pergunta": "Tutores baseados em LLM melhoram o desempenho acadêmico?",
    "P": "alunos de graduação",
    "I": "tutor baseado em LLM",
    "C": "ensino tradicional",
    "O": "desempenho acadêmico",
}


class TestAvaliarSuficiencia:
    def test_empty_abstract(self):
        reg = {"titulo": "Test", "abstract": ""}
        r = avaliar_suficiencia(reg, PROTOCOLO)
        assert r["suficiente"] is False
        assert r["tipo_insuficiencia"] == "vazio"

    def test_editorial_marker(self):
        reg = {
            "titulo": "An Editorial on AI",
            "abstract": "This editorial discusses the potential of AI in education. "
            "We present no empirical data but argue for further research.",
        }
        r = avaliar_suficiencia(reg, PROTOCOLO)
        assert r["suficiente"] is False
        assert "editorial" in r["marcadores"]

    def test_normal_academic_abstract(self):
        reg = {
            "titulo": "LLM Tutoring Study",
            "abstract": (
                "This quasi-experimental study evaluated the impact of a GPT-based tutoring chatbot "
                "on the academic performance of 120 undergraduate students enrolled in Calculus I at a "
                "Brazilian university. Students in the intervention group used the chatbot for homework "
                "support over one semester, while the control group received traditional instruction only. "
                "Final exam scores were compared using ANCOVA. The intervention group scored significantly "
                "higher than the control group. The results suggest that LLM-based tutoring can improve "
                "undergraduate calculus performance."
            ),
        }
        r = avaliar_suficiencia(reg, PROTOCOLO)
        assert r["suficiente"] is True
        assert r["tipo_insuficiencia"] is None

    def test_short_abstract_without_markers(self):
        reg = {
            "titulo": "Brief Note",
            "abstract": "A very short text about something with few words here.",
        }
        r = avaliar_suficiencia(reg, PROTOCOLO)
        assert r["suficiente"] is False
        assert r["n_palavras"] < 30
