"""LangGraph for GRADE certainty-of-evidence assessment (M6).

Fan-out per synthesis outcome -> evaluate 5 domains -> consolidate.
"""
from __future__ import annotations

import json
import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from prismai.checks.grade import (
    avaliar_imprecisao,
    avaliar_inconsistencia,
    avaliar_risco_vies,
    avaliar_vies_publicacao,
    certeza_final,
)
from prismai.core.envelope import Resposta
from prismai.core.models import GradeDomain, GradeResult


class GradeState(TypedDict):
    syntheses: list[dict]
    extractions: list[dict]
    protocolo: dict
    outcome_results: Annotated[list, operator.add]
    resultado: dict | None
    degradado: bool
    alertas: list
    traces: Annotated[list, operator.add]
    llm: Any


class OutcomeGradeState(TypedDict):
    synthesis: dict
    extractions: list[dict]
    protocolo: dict
    llm: Any


def _fan_out_desfechos(state: GradeState) -> list[Send]:
    return [
        Send("avaliar_dominios", {
            "synthesis": syn,
            "extractions": state["extractions"],
            "protocolo": state["protocolo"],
            "llm": state["llm"],
        })
        for syn in state["syntheses"]
    ]


def _avaliar_dominios(state: OutcomeGradeState) -> dict:
    syn = state["synthesis"]
    llm = state["llm"]
    study_effects = syn.get("study_effects", [])
    outcome_key = syn.get("outcome_key", "")
    measure = syn.get("measure", "smd")

    trace = {"agente": "avaliar_dominios_grade", "desfecho": outcome_key, "chamadas_llm": 0}

    # 1. Risk of bias (deterministic)
    rob_rating, rob_just = avaliar_risco_vies(study_effects)

    # 2. Inconsistency (deterministic)
    incon_rating, incon_just = avaliar_inconsistencia(syn.get("i2"), syn.get("k_studies", 0))

    # 3. Indirectness (LLM)
    indirect_rating = 0
    indirect_just = "Avaliação de indirectness não realizada"
    try:
        protocolo = state.get("protocolo", {})
        prompt = (
            f"Avalie a indirectness (aplicabilidade) do corpo de evidência para o desfecho "
            f"'{outcome_key}' em relação à pergunta PICO do protocolo.\n\n"
            f"PROTOCOLO:\nP: {protocolo.get('P', '?')}\nI: {protocolo.get('I', '?')}\n"
            f"C: {protocolo.get('C', '?')}\nO: {protocolo.get('O', '?')}\n\n"
            f"Estudos incluídos: {len([s for s in study_effects if s.get('incluido')])}\n\n"
            f"Responda com JSON: {{\"rating\": 0|-1|-2, \"justificativa\": \"...\"}}"
        )
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        indirect_rating = max(-2, min(0, int(parsed.get("rating", 0))))
        indirect_just = parsed.get("justificativa", "")
        trace["chamadas_llm"] = 1
    except Exception as e:
        indirect_just = f"Erro na avaliação de indirectness: {e}"

    # 4. Imprecision (deterministic)
    n_total = sum(s.get("n_total", 0) or 0 for s in study_effects if s.get("incluido"))
    imprec_rating, imprec_just = avaliar_imprecisao(
        syn.get("ci_low"), syn.get("ci_high"), measure, None, n_total or None,
    )

    # 5. Publication bias (deterministic)
    pub_rating, pub_just = avaliar_vies_publicacao(syn.get("egger_p"), syn.get("k_studies", 0))

    domains = [
        {"domain": "risk_of_bias", "rating": rob_rating, "justificativa": rob_just, "automatico": True},
        {"domain": "inconsistency", "rating": incon_rating, "justificativa": incon_just, "automatico": True},
        {"domain": "indirectness", "rating": indirect_rating, "justificativa": indirect_just, "automatico": False},
        {"domain": "imprecision", "rating": imprec_rating, "justificativa": imprec_just, "automatico": True},
        {"domain": "publication_bias", "rating": pub_rating, "justificativa": pub_just, "automatico": True},
    ]

    # Determine starting certainty (RCT -> high, observational -> low)
    starting = "high"
    ratings = [d["rating"] for d in domains]
    final = certeza_final(starting, ratings)

    result = {
        "outcome_key": outcome_key,
        "starting_certainty": starting,
        "domains": domains,
        "final_certainty": final,
        "k_studies": syn.get("k_studies", 0),
        "n_participants": n_total or None,
    }

    return {"outcome_results": [result], "traces": [trace]}


def _consolidar(state: GradeState) -> dict:
    results = state.get("outcome_results", [])
    alertas = list(state.get("alertas", []))
    degradado = state.get("degradado", False)
    return {
        "resultado": {"assessments": results},
        "alertas": alertas,
        "degradado": degradado,
    }


def build_grade_graph() -> StateGraph:
    builder = StateGraph(GradeState)
    builder.add_node("avaliar_dominios", _avaliar_dominios)
    builder.add_node("consolidar", _consolidar)
    builder.add_conditional_edges(START, _fan_out_desfechos, ["avaliar_dominios"])
    builder.add_edge("avaliar_dominios", "consolidar")
    builder.add_edge("consolidar", END)
    return builder.compile()


def assess_grade(
    syntheses: list[dict],
    extractions: list[dict],
    protocolo: dict,
    llm: Any,
) -> tuple[list[Resposta[GradeResult]], dict]:
    """Run GRADE assessment for all outcomes. Returns list of envelopes + metrics."""
    grafo = build_grade_graph()
    inicio = time.perf_counter()

    s0: GradeState = {
        "syntheses": syntheses,
        "extractions": extractions,
        "protocolo": protocolo,
        "outcome_results": [],
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
        metricas = {"latencia_s": round(lat, 2), "alertas": [f"GraphError: {e}"]}
        return [], metricas

    lat = time.perf_counter() - inicio
    resultado_dict = sf.get("resultado", {})
    assessments = resultado_dict.get("assessments", [])
    degradado = sf.get("degradado", False)
    alertas = sf.get("alertas", [])

    envelopes = []
    for a in assessments:
        gr = GradeResult(
            outcome_key=a["outcome_key"],
            starting_certainty=a.get("starting_certainty", "high"),
            domains=[GradeDomain(**d) for d in a.get("domains", [])],
            final_certainty=a.get("final_certainty", "high"),
        )
        envelopes.append(Resposta(
            resultado=gr,
            degradado=degradado,
            motivo_degradacao="; ".join(alertas) if degradado else None,
            alertas=alertas,
        ))

    metricas = {
        "latencia_s": round(lat, 2),
        "alertas": alertas,
        "traces": sf.get("traces", []),
    }
    return envelopes, metricas
