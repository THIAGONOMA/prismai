"""LangGraph for full-text eligibility assessment (F6).

Fan-out per criterion -> deterministic consolidator -> citation auditor.
"""
from __future__ import annotations

import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from prismai.core.envelope import Resposta
from prismai.core.models import CriterionResult, EligibilityResult, EvidenceSpanRef
from prismai.tools.chunk_retrieval import buscar_secoes_relevantes
from prismai.tools.literal import localizar_trecho_em_documento


class EligibilityState(TypedDict):
    protocolo: dict
    document: dict
    record: dict
    criteria_results: Annotated[list, operator.add]
    resultado: dict | None
    degradado: bool
    alertas: list
    traces: Annotated[list, operator.add]
    llm: Any


class CriterionState(TypedDict):
    criterion: str
    criterion_type: str  # "inclusion" | "exclusion"
    document: dict
    protocolo: dict
    llm: Any


def _fan_out_criterios(state: EligibilityState) -> list[Send]:
    """Dispatch one evaluation per criterion."""
    protocolo = state["protocolo"]
    sends = []
    for c in protocolo.get("inclusao", []):
        sends.append(Send("avaliar_criterio", {
            "criterion": c,
            "criterion_type": "inclusion",
            "document": state["document"],
            "protocolo": protocolo,
            "llm": state["llm"],
        }))
    for c in protocolo.get("exclusao", []):
        sends.append(Send("avaliar_criterio", {
            "criterion": c,
            "criterion_type": "exclusion",
            "document": state["document"],
            "protocolo": protocolo,
            "llm": state["llm"],
        }))
    return sends


_SKILL_PATH = "agents/skills/avaliar_criterio.md"


def _avaliar_criterio(state: CriterionState) -> dict:
    """Evaluate a single criterion against the document using LLM."""
    import json

    criterion = state["criterion"]
    sections = state["document"].get("sections", [])
    llm = state["llm"]

    relevant = buscar_secoes_relevantes(sections, criterion, top_k=3)
    context = "\n\n".join(
        f"[Seção: {s.get('title', '?')}, Página: {s.get('page', 0)}]\n{s.get('text', '')}"
        for s in relevant
    )

    prompt = (
        f"Avalie se o seguinte critério é atendido pelo documento.\n\n"
        f"CRITÉRIO: {criterion}\n"
        f"TIPO: {state['criterion_type']}\n\n"
        f"TRECHOS RELEVANTES DO DOCUMENTO:\n{context}\n\n"
        f"Responda SOMENTE com JSON válido no formato:\n"
        f'{{"met": true/false, "reasoning": "...", "evidence_text": "trecho literal do documento"}}'
    )

    trace = {
        "agente": "avaliar_criterio",
        "criterio": criterion,
        "chamadas_llm": 1,
        "tokens_entrada": 0,
        "tokens_saida": 0,
    }

    try:
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed = json.loads(content)
        met = parsed.get("met", False)
        reasoning = parsed.get("reasoning", "")
        evidence_text = parsed.get("evidence_text", "")

        spans = []
        if evidence_text:
            loc = localizar_trecho_em_documento(sections, evidence_text)
            if loc.get("encontrado") and not loc.get("parcial"):
                spans.append(EvidenceSpanRef(
                    page=loc.get("pagina", 0),
                    start=loc.get("start_offset", 0),
                    end=loc.get("end_offset", 0),
                    text=loc.get("trecho", evidence_text),
                ).model_dump())

        result = CriterionResult(
            criterion=criterion,
            met=met,
            evidence_spans=[EvidenceSpanRef(**s) for s in spans],
            reasoning=reasoning,
        )
        return {"criteria_results": [result.model_dump()]}
    except Exception as e:
        result = CriterionResult(
            criterion=criterion,
            met=False,
            evidence_spans=[],
            reasoning=f"Erro na avaliação: {e}",
        )
        trace["erro"] = str(e)
        return {"criteria_results": [result.model_dump()], "traces": [trace]}


def _consolidador(state: EligibilityState) -> dict:
    """Deterministic boolean consolidator — no LLM.

    If any exclusion criterion is met -> exclude.
    If all inclusion criteria are met -> include.
    Otherwise -> exclude with reason.
    """
    results = state["criteria_results"]
    protocolo = state["protocolo"]

    inclusion_criteria = set(protocolo.get("inclusao", []))
    exclusion_criteria = set(protocolo.get("exclusao", []))

    exclusion_met = []
    inclusion_results = {}

    for r in results:
        crit = r["criterion"]
        if crit in exclusion_criteria and r["met"]:
            exclusion_met.append(crit)
        if crit in inclusion_criteria:
            inclusion_results[crit] = r["met"]

    if exclusion_met:
        return {
            "resultado": {
                "decision": "exclude",
                "exclusion_reason": f"Critério(s) de exclusão atendido(s): {'; '.join(exclusion_met)}",
                "criteria_results": results,
                "confidence": "high",
            }
        }

    all_inclusion_met = all(inclusion_results.get(c, False) for c in inclusion_criteria)
    if all_inclusion_met:
        return {
            "resultado": {
                "decision": "include",
                "exclusion_reason": None,
                "criteria_results": results,
                "confidence": "high",
            }
        }

    missing = [c for c in inclusion_criteria if not inclusion_results.get(c, False)]
    return {
        "resultado": {
            "decision": "exclude",
            "exclusion_reason": f"Critério(s) de inclusão não atendido(s): {'; '.join(missing)}",
            "criteria_results": results,
            "confidence": "medium",
        }
    }


def _auditor_citacao(state: EligibilityState) -> dict:
    """Verify evidence spans actually exist in the document. Remove fabrications."""
    resultado = state["resultado"]
    if not resultado:
        return {}

    sections = state["document"].get("sections", [])
    verified_results = []
    alertas = list(state.get("alertas", []))
    removed = 0
    parciais = 0

    for cr in resultado.get("criteria_results", []):
        verified_spans = []
        for span in cr.get("evidence_spans", []):
            text = span.get("text", "")
            if not text:
                continue
            loc = localizar_trecho_em_documento(sections, text)
            if loc.get("encontrado") and not loc.get("parcial"):
                verified_spans.append(span)
            elif loc.get("parcial"):
                parciais += 1
            else:
                removed += 1
        cr_copy = dict(cr)
        cr_copy["evidence_spans"] = verified_spans
        verified_results.append(cr_copy)

    if removed:
        alertas.append(f"Auditor removeu {removed} citação(ões) fabricada(s)")
    if parciais:
        alertas.append(f"Auditor removeu {parciais} citação(ões) com casamento parcial")

    resultado_final = dict(resultado)
    resultado_final["criteria_results"] = verified_results
    return {"resultado": resultado_final, "alertas": alertas}


def build_eligibility_graph() -> StateGraph:
    builder = StateGraph(EligibilityState)
    builder.add_node("avaliar_criterio", _avaliar_criterio)
    builder.add_node("consolidador", _consolidador)
    builder.add_node("auditor_citacao", _auditor_citacao)
    builder.add_conditional_edges(START, _fan_out_criterios, ["avaliar_criterio"])
    builder.add_edge("avaliar_criterio", "consolidador")
    builder.add_edge("consolidador", "auditor_citacao")
    builder.add_edge("auditor_citacao", END)
    return builder.compile()


def evaluate_eligibility(
    document: dict,
    record: dict,
    protocolo: dict,
    llm: Any,
) -> tuple[Resposta[EligibilityResult], dict]:
    """Run the eligibility graph. Returns (envelope, metrics)."""
    grafo = build_eligibility_graph()
    inicio = time.perf_counter()

    s0: EligibilityState = {
        "protocolo": protocolo,
        "document": document,
        "record": record,
        "criteria_results": [],
        "resultado": None,
        "degradado": False,
        "alertas": [],
        "traces": [],
        "llm": llm,
    }

    try:
        sf = grafo.invoke(s0, {"recursion_limit": 50})
    except Exception as e:
        lat = time.perf_counter() - inicio
        r = EligibilityResult(decision="exclude", confidence="low", exclusion_reason=str(e))
        metricas = {
            "latencia_s": round(lat, 2),
            "alertas": [f"GraphError: {e}"],
        }
        resp = Resposta(resultado=r, degradado=True, motivo_degradacao=str(e), alertas=[str(e)])
        return resp, metricas

    lat = time.perf_counter() - inicio
    resultado_dict = sf.get("resultado", {})
    resultado = EligibilityResult(
        decision=resultado_dict.get("decision", "exclude"),
        exclusion_reason=resultado_dict.get("exclusion_reason"),
        criteria_results=[CriterionResult(**cr) for cr in resultado_dict.get("criteria_results", [])],
        confidence=resultado_dict.get("confidence", "low"),
    )
    degradado = sf.get("degradado", False)
    alertas = sf.get("alertas", [])
    metricas = {
        "latencia_s": round(lat, 2),
        "alertas": alertas,
        "traces": sf.get("traces", []),
    }
    resp = Resposta(
        resultado=resultado,
        degradado=degradado,
        motivo_degradacao="; ".join(alertas) if degradado else None,
        alertas=alertas,
    )
    return resp, metricas
