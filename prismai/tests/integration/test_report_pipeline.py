"""Integration tests for report pipeline with FakeLLM."""
from __future__ import annotations

import pytest

from prismai.graphs.report import draft_report
from prismai.persistence.memory import InMemoryRepository
from prismai.report.dossier import montar_dossie
from prismai.report.flow import contar_fluxo


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    def __init__(self, content: str = ""):
        self._content = content

    def invoke(self, prompt):
        return _FakeResponse(self._content)


@pytest.fixture
def dossie_completo():
    return {
        "protocol": {"pergunta": "X melhora Y?", "P": "adultos", "I": "X", "C": "placebo", "O": "Y",
                      "inclusao": ["RCT"], "exclusao": ["animais"]},
        "import_runs": [{"source": "openalex", "total_found": 100, "duplicates": 10, "imported": 90}],
        "records": [{"id": f"r{i}"} for i in range(90)],
        "decisions": [
            {"registro_id": f"r{i}", "screener": "primary", "decision": "exclude"} for i in range(60)
        ] + [
            {"registro_id": f"r{i}", "screener": "primary", "decision": "include"} for i in range(60, 90)
        ],
        "conflicts": [],
        "documents": [{"record_id": f"r{i}", "status": "extracted"} for i in range(60, 90)],
        "eligibility": [
            {"decision": "include", "record_id": f"r{i}"} for i in range(60, 80)
        ] + [
            {"decision": "exclude", "exclusion_reason": "sem dados", "record_id": f"r{i}"} for i in range(80, 90)
        ],
        "extractions": [{"record_id": f"r{i}"} for i in range(60, 80)],
        "rob": [{"record_id": f"r{i}", "overall_judgment": "low"} for i in range(60, 80)],
        "syntheses": [{"outcome_key": "pain", "k_studies": 5, "pooled_effect": 0.5,
                       "ci_low": 0.3, "ci_high": 0.7, "i2": 25.0}],
        "grade": [{"outcome_key": "pain", "final_certainty": "moderate"}],
    }


class TestReportPipeline:
    def test_full_pipeline_no_invented_numbers(self, dossie_completo):
        flow = contar_fluxo(dossie_completo)
        llm = FakeLLM(content="Foram identificados 100 registros, dos quais 10 duplicatas foram removidas. "
                              "Ao total, 90 registros foram triados e 60 excluídos.")
        resposta, metricas = draft_report(dossie_completo, flow, llm)
        assert not resposta.degradado
        assert len(resposta.alertas) == 0
        assert resposta.resultado.checklist.n_atendidos > 0
        assert len(resposta.resultado.sections) == 2

    def test_auditor_removes_invented_number(self, dossie_completo):
        flow = contar_fluxo(dossie_completo)
        llm = FakeLLM(content="Foram encontrados 999999 estudos relevantes e 100 registros identificados.")
        resposta, metricas = draft_report(dossie_completo, flow, llm)
        assert resposta.degradado
        assert any("999999" in a for a in resposta.alertas)
        for section in resposta.resultado.sections:
            assert 999999.0 not in section.numeros_citados


class TestReportPipelineWithRepo:
    @pytest.mark.asyncio
    async def test_end_to_end_with_repo(self):
        repo = InMemoryRepository()
        await repo.create_review("rev1")
        await repo.set_protocol("rev1", {"pergunta": "test?", "P": "p", "I": "i", "C": "c", "O": "o",
                                          "inclusao": ["a"], "exclusao": ["b"]})
        await repo.add_records("rev1", [{"id": "r1"}])
        await repo.add_decision("rev1", {"registro_id": "r1", "decision": "include"})

        dossie = await montar_dossie(repo, "rev1")
        flow = contar_fluxo(dossie)
        llm = FakeLLM(content="Um registro foi incluído. 1 estudo identificado.")
        resposta, _ = draft_report(dossie, flow, llm)
        assert resposta.resultado is not None
