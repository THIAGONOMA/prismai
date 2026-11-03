"""LangGraph for Risk of Bias assessment using RoB 2 (F8).

Fan-out per domain -> deterministic judgment -> citation auditor.
"""
from __future__ import annotations

import json
import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from prismai.checks.rob2 import ROB2_DOMAINS, julgar_dominio, julgar_geral
from prismai.core.envelope import Resposta
from prismai.core.models import DomainJudgment, RobResult, SignallingAnswer
from prismai.tools.chunk_retrieval import buscar_secoes_relevantes
from prismai.tools.literal import localizar_trecho_em_documento


class RobState(TypedDict):
    document: dict
    record: dict
    domain_results: Annotated[list, operator.add]
    resultado: dict | None
    degradado: bool
    alertas: list
    traces: Annotated[list, operator.add]
    llm: Any


class DomainState(TypedDict):
    domain: dict
    document: dict
    llm: Any


def _fan_out_dominios(state: RobState) -> list[Send]:
    return [
        Send("avaliar_dominio", {
            "domain": domain,
            "document": state["document"],
            "llm": state["llm"],
        })
        for domain in ROB2_DOMAINS
    ]


def _avaliar_dominio(state: DomainState) -> dict:
    domain = state["domain"]
    sections = state["document"].get("sections", [])
    llm = state["llm"]

    relevant = buscar_secoes_relevantes(sections, domain["name"], top_k=5)
    context = "\n\n".join(
        f"[Seção: {s.get('title', '?')}, Página: {s.get('page', 0)}]\n{s.get('text', '')}"
        for s in relevant
    )

    questions_text = "\n".join(
        f"- {q['id']}: {q['text']}" for q in domain["questions"]
    )

    prompt = (
        f"Avalie o risco de viés para o domínio '{domain['name']}' ({domain['description']}).\n\n"
        f"PERGUNTAS SINALIZADORAS:\n{questions_text}\n\n"
        f"TRECHOS RELEVANTES:\n{context}\n\n"
        f"Para cada pergunta, responda com uma das opções: Y (sim), PY (provavelmente sim), "
        f"PN (provavelmente não), N (não), NI (sem informação).\n\n"
        f"Responda SOMENTE com JSON válido:\n"
        f'[{{"question_id": "...", "answer": "Y|PY|PN|N|NI", "reasoning": "...", '
        f'"evidence_text": "trecho literal do documento"}}]'
    )

    trace = {"agente": "avaliar_dominio", "dominio": domain["id"], "chamadas_llm": 1}

    try:
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed = json.loads(content)
        if not isinstance(parsed, list):
            parsed = [parsed]

        answers = []
        for item in parsed:
            evidence_text = item.get("evidence_text", "")
            evidence_ref = None
            if evidence_text:
                loc = localizar_trecho_em_documento(sections, evidence_text)
                if loc.get("encontrado") and not loc.get("parcial"):
                    evidence_ref = {
                        "page": loc.get("pagina", 0),
                        "start": loc.get("start_offset", 0),
                        "end": loc.get("end_offset", 0),
                        "text": loc.get("trecho", evidence_text),
                    }

            answers.append({
                "question_id": item.get("question_id", ""),
                "answer": item.get("answer", "NI"),
                "reasoning": item.get("reasoning", ""),
                "evidence_ref": evidence_ref,
                "evidence_text": evidence_text,
            })

        domain_result = {
            "domain_id": domain["id"],
            "domain_name": domain["name"],
            "answers": answers,
        }

        return {"domain_results": [domain_result], "traces": [trace]}
    except Exception as e:
        trace["erro"] = str(e)
        return {
            "domain_results": [{
                "domain_id": domain["id"],
                "domain_name": domain["name"],
                "answers": [{"question_id": q["id"], "answer": "NI", "reasoning": str(e)} for q in domain["questions"]],
            }],
            "traces": [trace],
        }


def _julgamento(state: RobState) -> dict:
    domain_results = state["domain_results"]
    judged = []
    judgments = []

    for dr in domain_results:
        j = julgar_dominio(dr["domain_id"], dr["answers"])
        judgments.append(j)
        judged.append({**dr, "judgment": j})

    overall = julgar_geral(judgments)
    return {
        "domain_results": judged,
        "resultado": {"domains": judged, "overall": overall, "instrument": "rob2"},
    }


def _auditor_citacao(state: RobState) -> dict:
    sections = state["document"].get("sections", [])
    alertas = list(state.get("alertas", []))
    removed = 0

    resultado = state.get("resultado", {})
    domains = resultado.get("domains", [])
    parciais = 0

    for domain in domains:
        for answer in domain.get("answers", []):
            evidence_text = answer.get("evidence_text", "")
            if not evidence_text:
                continue
            loc = localizar_trecho_em_documento(sections, evidence_text)
            if loc.get("encontrado") and loc.get("parcial"):
                answer["evidence_ref"] = None
                parciais += 1
                continue
            if not loc.get("encontrado"):
                answer["evidence_ref"] = None
                removed += 1

    if removed:
        alertas.append(f"Auditor removeu {removed} citação(ões) não verificável(is)")
    if parciais:
        alertas.append(f"Auditor removeu {parciais} âncora(s) de casamento parcial")

    resultado["domains"] = domains
    return {"resultado": resultado, "alertas": alertas, "degradado": removed > 0}


def build_rob_graph() -> StateGraph:
    builder = StateGraph(RobState)
    builder.add_node("avaliar_dominio", _avaliar_dominio)
    builder.add_node("julgamento", _julgamento)
    builder.add_node("auditor_citacao", _auditor_citacao)
    builder.add_conditional_edges(START, _fan_out_dominios, ["avaliar_dominio"])
    builder.add_edge("avaliar_dominio", "julgamento")
    builder.add_edge("julgamento", "auditor_citacao")
    builder.add_edge("auditor_citacao", END)
    return builder.compile()


def assess_rob(
    document: dict,
    record: dict,
    llm: Any,
) -> tuple[Resposta[RobResult], dict]:
    """Run the RoB graph. Returns (envelope, metrics)."""
    grafo = build_rob_graph()
    inicio = time.perf_counter()

    s0: RobState = {
        "document": document,
        "record": record,
        "domain_results": [],
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
        r = RobResult(overall="high")
        metricas = {"latencia_s": round(lat, 2), "alertas": [f"GraphError: {e}"]}
        resp = Resposta(resultado=r, degradado=True, motivo_degradacao=str(e), alertas=[str(e)])
        return resp, metricas

    lat = time.perf_counter() - inicio
    resultado_dict = sf.get("resultado", {})

    domains = []
    for d in resultado_dict.get("domains", []):
        answers = []
        for a in d.get("answers", []):
            sa_kwargs: dict = {
                "question_id": a.get("question_id", ""),
                "answer": a.get("answer", "NI"),
                "reasoning": a.get("reasoning", ""),
            }
            answers.append(SignallingAnswer(**sa_kwargs))
        domains.append(DomainJudgment(
            domain=d.get("domain_id", d.get("domain_name", "")),
            judgment=d.get("judgment", "high"),
            answers=answers,
        ))

    resultado = RobResult(
        instrument="rob2",
        domains=domains,
        overall=resultado_dict.get("overall", "high"),
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
