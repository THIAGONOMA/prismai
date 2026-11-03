from prismai.agents.deterministic_auditor import auditor_deterministico

REGISTRO = {
    "titulo": "LLM Tutoring Study",
    "abstract": "This study evaluated the impact of a GPT-based tutoring chatbot on academic performance.",
}


class TestAuditorDeterministico:
    def test_valid_evidence_returned(self):
        triador = {
            "decision": "include",
            "reasons": ["motivo relevante"],
            "evidence": ["GPT-based tutoring chatbot"],
            "confidence": "high",
        }
        r = auditor_deterministico(triador, REGISTRO)
        assert r.decision == "include"
        assert len(r.evidence) == 1
        assert r.confidence == "high"

    def test_no_matching_evidence_include_lowers_confidence(self):
        triador = {
            "decision": "include",
            "reasons": ["motivo"],
            "evidence": ["something completely unrelated to the text"],
            "confidence": "high",
        }
        r = auditor_deterministico(triador, REGISTRO)
        assert r.decision == "include"
        assert len(r.evidence) == 0
        assert r.confidence != "high"

    def test_uncertain_clears_evidence(self):
        triador = {
            "decision": "uncertain",
            "reasons": ["unclear"],
            "evidence": ["GPT-based tutoring chatbot"],
            "confidence": "medium",
        }
        r = auditor_deterministico(triador, REGISTRO)
        assert r.decision == "uncertain"
        assert r.evidence == []
        assert r.confidence == "low"
