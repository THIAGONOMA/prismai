"""Unit tests for report/flow.py — PRISMA flow counter."""
from __future__ import annotations

from prismai.report.flow import contar_fluxo


def _base_dossie(**overrides):
    d = {
        "import_runs": [{"source": "openalex", "total_found": 100, "duplicates": 10}],
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
        "extractions": [],
        "rob": [],
        "syntheses": [],
        "grade": [],
    }
    d.update(overrides)
    return d


class TestFlowInvariantsClosing:
    def test_all_invariants_close(self):
        dossie = _base_dossie()
        flow = contar_fluxo(dossie)
        assert flow.discrepancias == []
        assert flow.identificados_total == 100
        assert flow.duplicatas_removidas == 10
        assert flow.registros_triados == 90
        assert flow.registros_excluidos == 60
        assert flow.fulltext_buscados == 30
        assert flow.fulltext_avaliados == 30
        assert flow.estudos_incluidos == 20
        assert flow.triagem_pendente == 0

    def test_invariant_1_breaks(self):
        decisions = [
            {"registro_id": f"r{i}", "screener": "primary", "decision": "exclude"} for i in range(60)
        ] + [
            {"registro_id": f"r{i}", "screener": "primary", "decision": "include"} for i in range(60, 85)
        ] + [
            {"registro_id": f"r{i}", "screener": "primary", "decision": "uncertain"} for i in range(85, 90)
        ]
        dossie = _base_dossie(decisions=decisions)
        flow = contar_fluxo(dossie)
        inv1 = [d for d in flow.discrepancias if d.invariante == "records_in_db"]
        assert len(inv1) == 1

    def test_invariant_2_always_balanced(self):
        """Invariant 2 (screening_balance) is tautological — triados = excluidos + buscados by construction."""
        dossie = _base_dossie()
        flow = contar_fluxo(dossie)
        inv2 = [d for d in flow.discrepancias if d.invariante == "screening_balance"]
        assert len(inv2) == 0
        assert flow.registros_triados == flow.registros_excluidos + flow.fulltext_buscados

    def test_invariant_4_breaks(self):
        elig = [
            {"decision": "include", "record_id": f"r{i}"} for i in range(60, 80)
        ] + [
            {"decision": "exclude", "exclusion_reason": "sem dados", "record_id": f"r{i}"} for i in range(80, 90)
        ] + [
            {"decision": "pending", "record_id": "r99"},
        ]
        dossie = _base_dossie(eligibility=elig)
        flow = contar_fluxo(dossie)
        inv4 = [d for d in flow.discrepancias if d.invariante == "eligibility_balance"]
        assert len(inv4) == 1


class TestFlowConflicts:
    def test_conflict_pending_counted(self):
        decisions = [
            {"registro_id": "r0", "screener": "primary", "decision": "include"},
            {"registro_id": "r0", "screener": "secondary", "decision": "exclude"},
        ]
        conflicts = [
            {"registro_id": "r0", "status": "pending", "decision_a": "include",
             "decision_b": "exclude", "screener_a": "primary", "screener_b": "secondary"},
        ]
        dossie = _base_dossie(
            records=[{"id": "r0"}],
            decisions=decisions,
            conflicts=conflicts,
            documents=[], eligibility=[],
        )
        flow = contar_fluxo(dossie)
        assert flow.conflitos_nao_resolvidos == 1
        assert flow.registros_triados == 0

    def test_conflict_resolved_uses_resolved_decision(self):
        decisions = [
            {"registro_id": "r0", "screener": "primary", "decision": "include"},
            {"registro_id": "r0", "screener": "secondary", "decision": "exclude"},
        ]
        conflicts = [
            {"registro_id": "r0", "status": "resolved", "resolved_decision": "include",
             "decision_a": "include", "decision_b": "exclude",
             "screener_a": "primary", "screener_b": "secondary"},
        ]
        dossie = _base_dossie(
            records=[{"id": "r0"}],
            decisions=decisions,
            conflicts=conflicts,
            documents=[], eligibility=[],
        )
        flow = contar_fluxo(dossie)
        assert flow.conflitos_nao_resolvidos == 0
        assert flow.fulltext_buscados == 1


class TestFlowDualScreening:
    def test_dual_screening_no_double_count(self):
        decisions = [
            {"registro_id": "r0", "screener": "primary", "decision": "include"},
            {"registro_id": "r0", "screener": "secondary", "decision": "include"},
        ]
        dossie = _base_dossie(
            records=[{"id": "r0"}],
            decisions=decisions,
            conflicts=[],
            documents=[], eligibility=[],
        )
        flow = contar_fluxo(dossie)
        assert flow.registros_triados == 1
        assert flow.fulltext_buscados == 1


class TestFlowMultiSource:
    def test_multi_source_counts(self):
        import_runs = [
            {"source": "openalex", "total_found": 50, "duplicates": 5},
            {"source": "crossref", "total_found": 30, "duplicates": 3},
        ]
        dossie = _base_dossie(import_runs=import_runs)
        flow = contar_fluxo(dossie)
        assert flow.identificados_por_fonte == {"openalex": 50, "crossref": 30}
        assert flow.identificados_total == 80
        assert flow.duplicatas_removidas == 8
