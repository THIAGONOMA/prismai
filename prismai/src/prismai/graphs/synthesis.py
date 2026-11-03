"""LangGraph for quantitative synthesis / meta-analysis (M6).

Fan-out per outcome -> map studies -> compute effects -> pool -> audit citations.
"""
from __future__ import annotations

import json
import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from prismai.core.envelope import Resposta
from prismai.core.models import StudyEffect, SynthesisResult
from prismai.core.synthesis_config import carregar_synthesis_config
from prismai.synthesis.bias import egger_test
from prismai.synthesis.effects import efeito_estudo
from prismai.synthesis.pooling import agrupar


class SynthesisState(TypedDict):
    config: dict
    extractions: list[dict]
    rob_assessments: list[dict]
    protocolo: dict
    outcome_results: Annotated[list, operator.add]
    resultado: dict | None
    degradado: bool
    alertas: list
    traces: Annotated[list, operator.add]
    llm: Any


class OutcomeState(TypedDict):
    outcome: dict
    extractions: list[dict]
    rob_assessments: list[dict]
    llm: Any


def _fan_out_desfechos(state: SynthesisState) -> list[Send]:
    cfg = carregar_synthesis_config(state["config"])
    if cfg is None:
        return []
    return [
        Send("mapear_estudos", {
            "outcome": oc.model_dump(),
            "extractions": state["extractions"],
            "rob_assessments": state["rob_assessments"],
            "llm": state["llm"],
        })
        for oc in cfg.outcomes
    ]


def _mapear_estudos(state: OutcomeState) -> dict:
    outcome = state["outcome"]
    extractions = state["extractions"]
    rob_assessments = state["rob_assessments"]
    llm = state["llm"]

    outcome_key = outcome["key"]
    sinonimos = outcome.get("sinonimos", [])
    measure = outcome["measure"]

    rob_by_record = {r["record_id"]: r.get("overall_judgment", "low") for r in rob_assessments}

    prompt = (
        f"Dado os seguintes estudos e seus desfechos extraídos, identifique quais medem o desfecho "
        f"'{outcome.get('nome', outcome_key)}' (sinônimos: {', '.join(sinonimos)}).\n\n"
        "ESTUDOS:\n"
    )
    for ext in extractions:
        rid = ext.get("record_id", "")
        cells = {c["field"]: c.get("value") for c in ext.get("cells", [])}
        prompt += (
            f"- {rid}: desfecho_primario={cells.get('desfecho_primario', '?')}, "
            f"desfechos_secundarios={cells.get('desfechos_secundarios', '?')}, "
            f"instrumento={cells.get('instrumento_medida', '?')}\n"
        )
    prompt += (
        "\nResponda com JSON: [{'record_id': '...', 'incluido': true/false, "
        "'motivo': 'razão se excluído'}]\n"
    )

    trace = {"agente": "mapear_estudos", "desfecho": outcome_key, "chamadas_llm": 1}
    study_effects = []

    try:
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        mapping = json.loads(content)
        if not isinstance(mapping, list):
            mapping = [mapping]
    except Exception as e:
        trace["erro"] = str(e)
        mapping = [{"record_id": ext.get("record_id", ""), "incluido": True} for ext in extractions]

    mapped_ids = {m["record_id"]: m for m in mapping}

    for ext in extractions:
        rid = ext.get("record_id", "")
        m_info = mapped_ids.get(rid, {"incluido": False, "motivo": "não mapeado pelo LLM"})
        cells = {c["field"]: c.get("value") for c in ext.get("cells", [])}
        incluido = m_info.get("incluido", False)
        motivo = m_info.get("motivo")

        se_dict: dict[str, Any] = {
            "record_id": rid,
            "incluido": incluido,
            "motivo_exclusao": motivo if not incluido else None,
            "rob": rob_by_record.get(rid, "low"),
        }

        if incluido:
            effect = efeito_estudo(cells, measure)
            if "erro" in effect:
                se_dict["incluido"] = False
                se_dict["motivo_exclusao"] = effect["erro"]
            else:
                se_dict.update({
                    "yi": effect["yi"],
                    "vi": effect["vi"],
                    "se": effect["se"],
                    "ci_low": effect["ci_low"],
                    "ci_high": effect["ci_high"],
                    "n_total": effect.get("n_total"),
                })

        study_effects.append(se_dict)

    included_effects = [s for s in study_effects if s.get("incluido") and s.get("yi") is not None]
    pooled = agrupar(included_effects, model=outcome.get("model", "random"))

    if pooled.get("weights"):
        for i, se in enumerate(included_effects):
            if i < len(pooled["weights"]):
                se["weight_random"] = pooled["weights"][i]

    egger = egger_test(included_effects)

    n_total = sum(s.get("n_total", 0) or 0 for s in included_effects)
    result = {
        "outcome_key": outcome_key,
        "measure": measure,
        "model": "random",
        "k_studies": pooled.get("k", 0),
        "n_participants": n_total or None,
        "pooled_effect": pooled.get("pooled_effect"),
        "se": pooled.get("se"),
        "ci_low": pooled.get("ci_low"),
        "ci_high": pooled.get("ci_high"),
        "p_value": pooled.get("p_value"),
        "tau2": pooled.get("tau2"),
        "q": pooled.get("q"),
        "q_p": pooled.get("q_p"),
        "i2": pooled.get("i2"),
        "prediction_low": pooled.get("prediction_low"),
        "prediction_high": pooled.get("prediction_high"),
        "egger_intercept": egger.get("intercept"),
        "egger_p": egger.get("p"),
        "study_effects": study_effects,
    }

    return {"outcome_results": [result], "traces": [trace]}


def _consolidar(state: SynthesisState) -> dict:
    results = state.get("outcome_results", [])
    alertas = list(state.get("alertas", []))
    degradado = state.get("degradado", False)

    for r in results:
        if r.get("k_studies", 0) == 0:
            alertas.append(f"Desfecho '{r['outcome_key']}' sem estudos incluídos")
            degradado = True

    return {
        "resultado": {"outcomes": results},
        "alertas": alertas,
        "degradado": degradado,
    }


def build_synthesis_graph() -> StateGraph:
    builder = StateGraph(SynthesisState)
    builder.add_node("mapear_estudos", _mapear_estudos)
    builder.add_node("consolidar", _consolidar)
    builder.add_conditional_edges(START, _fan_out_desfechos, ["mapear_estudos"])
    builder.add_edge("mapear_estudos", "consolidar")
    builder.add_edge("consolidar", END)
    return builder.compile()


def synthesize(
    config: dict,
    extractions: list[dict],
    rob_assessments: list[dict],
    protocolo: dict,
    llm: Any,
) -> tuple[list[Resposta[SynthesisResult]], dict]:
    """Run synthesis for all outcomes. Returns list of envelopes + metrics."""
    grafo = build_synthesis_graph()
    inicio = time.perf_counter()

    s0: SynthesisState = {
        "config": config,
        "extractions": extractions,
        "rob_assessments": rob_assessments,
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
    resultado_dict = sf.get("resultado") or {}
    outcomes = resultado_dict.get("outcomes", [])
    degradado = sf.get("degradado", False)
    alertas = sf.get("alertas", [])

    envelopes = []
    for oc in outcomes:
        sr = SynthesisResult(
            outcome_key=oc["outcome_key"],
            measure=oc.get("measure", ""),
            model=oc.get("model", "random"),
            k_studies=oc.get("k_studies", 0),
            pooled_effect=oc.get("pooled_effect"),
            se=oc.get("se"),
            ci_low=oc.get("ci_low"),
            ci_high=oc.get("ci_high"),
            p_value=oc.get("p_value"),
            tau2=oc.get("tau2"),
            q=oc.get("q"),
            i2=oc.get("i2"),
            prediction_low=oc.get("prediction_low"),
            prediction_high=oc.get("prediction_high"),
            egger_intercept=oc.get("egger_intercept"),
            egger_p=oc.get("egger_p"),
            study_effects=[StudyEffect(**s) for s in oc.get("study_effects", [])],
        )
        envelopes.append(Resposta(
            resultado=sr,
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
