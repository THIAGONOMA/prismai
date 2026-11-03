"""Deterministic PRISMA flow counter. Derives counts and checks 4 invariants."""
from __future__ import annotations

from collections import Counter

from prismai.core.models import FlowDiscrepancy, PrismaFlowCounts


def contar_fluxo(dossie: dict) -> PrismaFlowCounts:
    import_runs = dossie.get("import_runs", [])
    records = dossie.get("records", [])
    decisions = dossie.get("decisions", [])
    conflicts = dossie.get("conflicts", [])
    documents = dossie.get("documents", [])
    eligibility = dossie.get("eligibility", [])

    source_counts: Counter[str] = Counter()
    total_found = 0
    total_dups = 0
    for run in import_runs:
        source_counts[run.get("source", "unknown")] += run.get("total_found", 0)
        total_found += run.get("total_found", 0)
        total_dups += run.get("duplicates", 0)

    conflict_map: dict[str, dict] = {}
    for c in conflicts:
        conflict_map[c["registro_id"]] = c

    conflitos_nao_resolvidos = 0
    final_decisions: dict[str, str] = {}

    decided_ids: set[str] = set()
    primary_decisions: dict[str, dict] = {}
    for d in decisions:
        rid = d.get("registro_id", "")
        screener = d.get("screener", "primary")
        if screener == "primary" or rid not in primary_decisions:
            if rid not in primary_decisions or screener == "primary":
                primary_decisions[rid] = d

    for rid, d in primary_decisions.items():
        decided_ids.add(rid)
        if rid in conflict_map:
            c = conflict_map[rid]
            if c.get("status") == "resolved" and c.get("resolved_decision"):
                final_decisions[rid] = c["resolved_decision"]
            else:
                conflitos_nao_resolvidos += 1
        else:
            final_decisions[rid] = d.get("decision", "")

    registros_triados = sum(1 for dec in final_decisions.values() if dec in ("include", "exclude"))
    registros_excluidos = sum(1 for dec in final_decisions.values() if dec == "exclude")
    fulltext_buscados = sum(1 for dec in final_decisions.values() if dec == "include")

    all_record_ids = {r.get("id", "") for r in records}
    triagem_pendente = len(all_record_ids - decided_ids)

    doc_record_ids = {d.get("record_id", "") for d in documents}
    failed_statuses = {"failed", "requires_manual_transcription"}
    failed_docs = sum(1 for d in documents if d.get("status") in failed_statuses)
    included_without_doc = sum(
        1 for rid, dec in final_decisions.items() if dec == "include" and rid not in doc_record_ids
    )
    fulltext_nao_recuperados = failed_docs + included_without_doc

    fulltext_avaliados = len(eligibility)
    excl_reasons: Counter[str] = Counter()
    estudos_incluidos = 0
    for e in eligibility:
        if e.get("decision") == "exclude":
            reason = e.get("exclusion_reason") or "não especificado"
            excl_reasons[reason] += 1
        elif e.get("decision") == "include":
            estudos_incluidos += 1

    flow = PrismaFlowCounts(
        identificados_por_fonte=dict(source_counts),
        identificados_total=total_found,
        duplicatas_removidas=total_dups,
        registros_triados=registros_triados,
        registros_excluidos=registros_excluidos,
        fulltext_buscados=fulltext_buscados,
        fulltext_nao_recuperados=fulltext_nao_recuperados,
        fulltext_avaliados=fulltext_avaliados,
        fulltext_excluidos_por_motivo=dict(excl_reasons),
        estudos_incluidos=estudos_incluidos,
        triagem_pendente=triagem_pendente,
        conflitos_nao_resolvidos=conflitos_nao_resolvidos,
    )

    discrepancias: list[FlowDiscrepancy] = []

    esperado_inv1 = len(records)
    encontrado_inv1 = registros_triados + triagem_pendente + conflitos_nao_resolvidos
    if esperado_inv1 != encontrado_inv1:
        discrepancias.append(FlowDiscrepancy(
            invariante="records_in_db",
            esperado=esperado_inv1,
            encontrado=encontrado_inv1,
            detalhe="identificados - duplicatas deveria ser triados + pendente + conflitos",
        ))

    esperado_inv2 = registros_triados
    encontrado_inv2 = registros_excluidos + fulltext_buscados
    if esperado_inv2 != encontrado_inv2:
        discrepancias.append(FlowDiscrepancy(
            invariante="screening_balance",
            esperado=esperado_inv2,
            encontrado=encontrado_inv2,
            detalhe="registros_triados deveria ser registros_excluidos + fulltext_buscados",
        ))

    not_yet_assessed = fulltext_buscados - fulltext_nao_recuperados - fulltext_avaliados
    esperado_inv3 = fulltext_buscados
    encontrado_inv3 = fulltext_nao_recuperados + fulltext_avaliados + max(0, not_yet_assessed)
    if esperado_inv3 != encontrado_inv3:
        discrepancias.append(FlowDiscrepancy(
            invariante="fulltext_balance",
            esperado=esperado_inv3,
            encontrado=encontrado_inv3,
            detalhe="fulltext_buscados deveria ser nao_recuperados + avaliados + pendentes",
        ))

    esperado_inv4 = fulltext_avaliados
    encontrado_inv4 = sum(excl_reasons.values()) + estudos_incluidos
    if esperado_inv4 != encontrado_inv4:
        discrepancias.append(FlowDiscrepancy(
            invariante="eligibility_balance",
            esperado=esperado_inv4,
            encontrado=encontrado_inv4,
            detalhe="fulltext_avaliados deveria ser excluidos_por_motivo + estudos_incluidos",
        ))

    flow.discrepancias = discrepancias
    return flow
