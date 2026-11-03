from __future__ import annotations

import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from prismai.agents.auditor import agente_auditor
from prismai.agents.coletor import agente_coletor
from prismai.agents.triador import agente_triador
from prismai.core.envelope import Resposta
from prismai.core.models import ScreeningResult


class ScreeningState(TypedDict):
    modo: str
    protocolo: dict
    registro: dict | None
    query: str | None
    max_results: int
    registros_coletados: list
    triador_output: dict | None
    resultado: dict | None
    degradado: bool
    alertas: list
    traces: Annotated[list, operator.add]
    llm: Any
    llm_auditor: Any


def _rota_entrada(state: ScreeningState) -> str:
    return "coletor" if state["modo"] == "query" else "triador"


def _coletor(state: ScreeningState) -> dict:
    alertas = list(state.get("alertas", []))
    try:
        regs, trace = agente_coletor(state["query"], state["max_results"])
    except Exception as e:
        alertas.append(f"DEGRADADO: Coletor falhou ({type(e).__name__})")
        trace = {
            "agente": "coletor",
            "tipo": "etapa_de_fluxo",
            "chamadas_llm": 0,
            "chamadas_ferramentas": 0,
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "latencia_s": 0,
            "tools": [],
            "erro": str(e),
        }
        return {"registros_coletados": [], "registro": None, "degradado": True, "alertas": alertas, "traces": [trace]}
    validos = [r for r in regs if "erro" not in r and r.get("titulo") and r.get("abstract")]
    registro = validos[0] if validos else None
    if not registro:
        alertas.append("DEGRADADO: Coletor nao encontrou registros validos")
    return {
        "registros_coletados": regs,
        "registro": registro,
        "degradado": not bool(registro),
        "alertas": alertas,
        "traces": [trace],
    }


def _triador(state: ScreeningState) -> dict:
    reg = state["registro"]
    alertas = list(state.get("alertas", []))
    llm = state["llm"]
    if not reg:
        trace = {
            "agente": "triador",
            "tipo": "agente",
            "chamadas_llm": 0,
            "chamadas_ferramentas": 0,
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "latencia_s": 0,
            "tools": [],
            "nota": "sem registro para triar",
        }
        return {
            "triador_output": {
                "decision": "uncertain", "reasons": ["Sem registro."], "evidence": [], "confidence": "low"
            },
            "degradado": True,
            "alertas": alertas,
            "traces": [trace],
        }
    dados, trace, degradou = agente_triador(reg, state["protocolo"], llm, alertas)
    return {
        "triador_output": dados,
        "degradado": state.get("degradado", False) or degradou,
        "alertas": alertas,
        "traces": [trace],
    }


def _auditor(state: ScreeningState) -> dict:
    reg = state["registro"]
    alertas = list(state.get("alertas", []))
    llm = state.get("llm_auditor") or state["llm"]
    if not reg:
        trace = {
            "agente": "auditor",
            "tipo": "agente",
            "chamadas_llm": 0,
            "chamadas_ferramentas": 0,
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "latencia_s": 0,
            "tools": [],
            "nota": "sem registro para auditar",
        }
        r = ScreeningResult(decision="uncertain", reasons=["Sem registro."], evidence=[], confidence="low")
        return {"resultado": r.model_dump(), "degradado": True, "alertas": alertas, "traces": [trace]}
    resultado, trace, degradou = agente_auditor(state["triador_output"], reg, llm, alertas)
    return {
        "resultado": resultado.model_dump(),
        "degradado": state.get("degradado", False) or degradou,
        "alertas": alertas,
        "traces": [trace],
    }


def build_screening_graph() -> StateGraph:
    builder = StateGraph(ScreeningState)
    builder.add_node("coletor", _coletor)
    builder.add_node("triador", _triador)
    builder.add_node("auditor", _auditor)
    builder.add_conditional_edges(START, _rota_entrada, {"coletor": "coletor", "triador": "triador"})
    builder.add_edge("coletor", "triador")
    builder.add_edge("triador", "auditor")
    builder.add_edge("auditor", END)
    return builder.compile()


def _extrair_metricas(state_final: dict, inicio: float) -> dict:
    traces = state_final["traces"]
    lat = time.perf_counter() - inicio
    return {
        "latencia_s": round(lat, 2),
        "chamadas_llm": sum(t.get("chamadas_llm", 0) for t in traces),
        "chamadas_ferramentas": sum(t.get("chamadas_ferramentas", 0) for t in traces),
        "tokens_entrada": sum(t.get("tokens_entrada", 0) for t in traces),
        "tokens_saida": sum(t.get("tokens_saida", 0) for t in traces),
        "erro_parse": None,
        "agentes": [t["agente"] for t in traces if t.get("tipo", "agente") == "agente"],
        "etapas_fluxo": [t["agente"] for t in traces if t.get("tipo") == "etapa_de_fluxo"],
        "skills_carregadas": list({t.get("skill", "") for t in traces if t.get("skill")}),
        "trace": {t["agente"]: t for t in traces},
        "alertas": state_final.get("alertas", []),
    }


def screen_v4(
    registro: dict, protocolo: dict, llm: Any, llm_auditor: Any = None,
) -> tuple[Resposta[ScreeningResult], dict]:
    grafo = build_screening_graph()
    inicio = time.perf_counter()
    s0: ScreeningState = {
        "modo": "registro",
        "protocolo": protocolo,
        "registro": registro,
        "query": None,
        "max_results": 0,
        "registros_coletados": [],
        "triador_output": None,
        "resultado": None,
        "degradado": False,
        "alertas": [],
        "traces": [],
        "llm": llm,
        "llm_auditor": llm_auditor,
    }
    try:
        sf = grafo.invoke(s0, {"recursion_limit": 8})
    except Exception:
        lat = time.perf_counter() - inicio
        r = ScreeningResult(decision="uncertain", reasons=["Limite de passos atingido."], evidence=[], confidence="low")
        m = {
            "latencia_s": round(lat, 2),
            "chamadas_llm": 0,
            "chamadas_ferramentas": 0,
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "erro_parse": None,
            "agentes": [],
            "etapas_fluxo": [],
            "trace": {},
            "alertas": ["DEGRADADO: GraphRecursionError"],
        }
        resp = Resposta(
            resultado=r, degradado=True,
            motivo_degradacao="Limite de passos do grafo atingido",
            alertas=["GraphRecursionError"],
        )
        return resp, m

    metricas = _extrair_metricas(sf, inicio)
    resultado = ScreeningResult(**sf["resultado"])
    degradado = sf.get("degradado", False)
    motivo = "; ".join(sf.get("alertas", [])) if degradado else None
    resp = Resposta(
        resultado=resultado, degradado=degradado,
        motivo_degradacao=motivo, alertas=sf.get("alertas", []),
    )
    return resp, metricas
