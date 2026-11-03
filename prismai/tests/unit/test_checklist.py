"""Unit tests for report/checklist.py — PRISMA 2020 checklist."""
from __future__ import annotations

from prismai.core.models import PrismaFlowCounts
from prismai.report.checklist import PRISMA2020_ITEMS, preencher_checklist


def _empty_dossie():
    return {
        "protocol": None,
        "import_runs": [],
        "records": [],
        "decisions": [],
        "conflicts": [],
        "documents": [],
        "eligibility": [],
        "extractions": [],
        "rob": [],
        "syntheses": [],
        "grade": [],
    }


def _zero_flow():
    return PrismaFlowCounts()


class TestChecklist:
    def test_all_27_items_present(self):
        result = preencher_checklist(_empty_dossie(), _zero_flow())
        assert len(result.itens) == len(PRISMA2020_ITEMS)
        assert len(result.itens) >= 27

    def test_empty_dossie_has_low_count(self):
        result = preencher_checklist(_empty_dossie(), _zero_flow())
        assert result.n_atendidos == 0

    def test_item_with_source_attended(self):
        dossie = _empty_dossie()
        dossie["import_runs"] = [{"source": "openalex", "total_found": 10}]
        result = preencher_checklist(dossie, _zero_flow())
        item6 = next(i for i in result.itens if i.numero == "6")
        assert item6.atendido is True

    def test_item_without_source_not_attended(self):
        result = preencher_checklist(_empty_dossie(), _zero_flow())
        item6 = next(i for i in result.itens if i.numero == "6")
        assert item6.atendido is False

    def test_protocol_enables_multiple_items(self):
        dossie = _empty_dossie()
        dossie["protocol"] = {
            "pergunta": "Does X improve Y?",
            "P": "adults", "I": "X", "C": "placebo", "O": "Y",
            "inclusao": ["RCT"], "exclusao": ["non-human"],
        }
        flow = PrismaFlowCounts(registros_triados=5)
        result = preencher_checklist(dossie, flow)
        item1 = next(i for i in result.itens if i.numero == "1")
        item4 = next(i for i in result.itens if i.numero == "4")
        item5 = next(i for i in result.itens if i.numero == "5")
        assert item1.atendido is True
        assert item4.atendido is True
        assert item5.atendido is True

    def test_discussion_items_always_false(self):
        dossie = _empty_dossie()
        dossie["protocol"] = {"pergunta": "q", "P": "p", "I": "i", "C": "c", "O": "o", "inclusao": ["a"], "exclusao": ["b"]}
        dossie["import_runs"] = [{"source": "x", "total_found": 1, "query": "q"}]
        dossie["records"] = [{"id": "r1"}]
        dossie["decisions"] = [{"registro_id": "r1", "screener": "primary", "decision": "include"}]
        dossie["extractions"] = [{"record_id": "r1"}]
        dossie["rob"] = [{"record_id": "r1"}]
        dossie["syntheses"] = [{"outcome_key": "pain"}]
        dossie["grade"] = [{"outcome_key": "pain"}]
        dossie["eligibility"] = [{"decision": "include"}]
        flow = PrismaFlowCounts(registros_triados=1)
        result = preencher_checklist(dossie, flow)
        for num in ["23a", "23b", "23c", "23d"]:
            item = next(i for i in result.itens if i.numero == num)
            assert item.atendido is False, f"Item {num} should not be attended"
