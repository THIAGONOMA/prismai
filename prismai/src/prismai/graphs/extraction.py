"""LangGraph for structured data extraction (F7).

Fan-out per schema block -> numeric verifier -> citation auditor.
"""
from __future__ import annotations

import json
import operator
import time
from collections import defaultdict
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from prismai.checks.numeric import verificar_consistencia
from prismai.core.envelope import Resposta
from prismai.core.extraction_schema import carregar_schema
from prismai.core.models import EvidenceSpanRef, ExtractedCell, ExtractionResult
from prismai.tools.chunk_retrieval import buscar_secoes_relevantes
from prismai.tools.literal import localizar_trecho_em_documento


class ExtractionState(TypedDict):
    protocolo: dict
    document: dict
    record: dict
    schema: dict
    cells: Annotated[list, operator.add]
    resultado: dict | None
    degradado: bool
    alertas: list
    traces: Annotated[list, operator.add]
    llm: Any


class BlockState(TypedDict):
    block: str
    fields: list[dict]
    document: dict
    llm: Any


def _fan_out_blocos(state: ExtractionState) -> list[Send]:
    schema = carregar_schema(state.get("schema"))
    blocks: dict[str, list[dict]] = defaultdict(list)
    for f in schema.fields:
        blocks[f.block].append(f.model_dump())
    return [
        Send("extrair_bloco", {
            "block": block,
            "fields": fields,
            "document": state["document"],
            "llm": state["llm"],
        })
        for block, fields in blocks.items()
    ]


def _extrair_bloco(state: BlockState) -> dict:
    block = state["block"]
    fields = state["fields"]
    sections = state["document"].get("sections", [])
    llm = state["llm"]

    relevant = buscar_secoes_relevantes(sections, block, top_k=5)
    context = "\n\n".join(
        f"[Seção: {s.get('title', '?')}, Página: {s.get('page', 0)}]\n{s.get('text', '')}"
        for s in relevant
    )

    field_desc = "\n".join(
        f"- {f['name']} ({f['tipo']}): {f['descricao']}" for f in fields
    )

    prompt = (
        f"Extraia os seguintes campos do bloco '{block}' a partir do documento.\n\n"
        f"CAMPOS:\n{field_desc}\n\n"
        f"TRECHOS RELEVANTES:\n{context}\n\n"
        f"Responda SOMENTE com JSON válido: um array de objetos, cada um com:\n"
        f'{{"field": "nome_campo", "value": ..., "evidence_text": "trecho literal do documento"}}\n'
        f"Se não encontrar o valor, use null."
    )

    trace = {"agente": "extrair_bloco", "bloco": block, "chamadas_llm": 1}

    try:
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed = json.loads(content)
        if not isinstance(parsed, list):
            parsed = [parsed]

        field_types = {f["name"]: f["tipo"] for f in fields}
        cells = []
        for item in parsed:
            fname = item.get("field", "")
            value = item.get("value")
            evidence_text = item.get("evidence_text", "")

            vtype = field_types.get(fname, "text")
            page = None
            start_offset = None
            end_offset = None
            flags: list[str] = []
            needs_human = False

            if evidence_text:
                loc = localizar_trecho_em_documento(sections, evidence_text)
                if loc.get("encontrado") and not loc.get("parcial"):
                    page = loc.get("pagina", 0)
                    start_offset = loc.get("start_offset", 0)
                    end_offset = loc.get("end_offset", 0)
                    evidence_text = loc.get("trecho", evidence_text)
                elif loc.get("encontrado") and loc.get("parcial"):
                    needs_human = True
                    flags.append("casamento parcial")

            cells.append({
                "field": fname,
                "block": block,
                "value": value,
                "value_type": vtype,
                "page": page,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "evidence_text": evidence_text if evidence_text else None,
                "confidence": "medium" if evidence_text else "low",
                "needs_human_confirmation": needs_human,
                "flags": flags,
            })

        return {"cells": cells, "traces": [trace]}
    except Exception as e:
        trace["erro"] = str(e)
        return {"cells": [], "traces": [trace]}


def _verificador_numerico(state: ExtractionState) -> dict:
    cells = state["cells"]
    flags = verificar_consistencia(cells)
    alertas = list(state.get("alertas", []))

    if flags:
        alertas.extend(flags)
        for cell in cells:
            if cell.get("value_type") in ("number", "integer") or cell.get("block") == "estatisticas":
                cell["needs_human_confirmation"] = True
                for f in flags:
                    if cell["field"] in f:
                        cell.setdefault("flags", []).append(f)

    return {"cells": cells, "alertas": alertas}


def _auditor_citacao(state: ExtractionState) -> dict:
    cells = state["cells"]
    sections = state["document"].get("sections", [])
    alertas = list(state.get("alertas", []))
    removed = 0

    for cell in cells:
        evidence_text = cell.get("evidence_text", "")
        if not evidence_text:
            continue
        loc = localizar_trecho_em_documento(sections, evidence_text)
        if loc.get("encontrado") and loc.get("parcial"):
            cell["page"] = None
            cell["start_offset"] = None
            cell["end_offset"] = None
            cell["needs_human_confirmation"] = True
            flags = cell.setdefault("flags", [])
            if "casamento parcial" not in flags:
                flags.append("casamento parcial")
            continue
        if not loc.get("encontrado"):
            cell["value"] = None
            cell["confidence"] = "low"
            cell.setdefault("flags", []).append("citação não verificada")
            removed += 1

    if removed:
        alertas.append(f"Auditor invalidou {removed} célula(s) com citação não verificável")

    schema = carregar_schema(state.get("schema"))
    consistency_flags = verificar_consistencia(cells)

    resultado = ExtractionResult(
        schema_version=schema.version,
        cells=[ExtractedCell(
            field=c["field"], block=c["block"], value=c["value"],
            value_type=c.get("value_type", "text"),
            evidence=EvidenceSpanRef(
                page=c["page"], start=c["start_offset"],
                end=c["end_offset"], text=c["evidence_text"],
            ) if c.get("page") is not None and c.get("evidence_text") else None,
            confidence=c.get("confidence", "low"),
            needs_human_confirmation=c.get("needs_human_confirmation", False),
            flags=c.get("flags", []),
        ) for c in cells],
        consistency_flags=consistency_flags,
    )

    return {
        "resultado": resultado.model_dump(),
        "alertas": alertas,
        "degradado": bool(consistency_flags) or removed > 0,
    }


def build_extraction_graph() -> StateGraph:
    builder = StateGraph(ExtractionState)
    builder.add_node("extrair_bloco", _extrair_bloco)
    builder.add_node("verificador_numerico", _verificador_numerico)
    builder.add_node("auditor_citacao", _auditor_citacao)
    builder.add_conditional_edges(START, _fan_out_blocos, ["extrair_bloco"])
    builder.add_edge("extrair_bloco", "verificador_numerico")
    builder.add_edge("verificador_numerico", "auditor_citacao")
    builder.add_edge("auditor_citacao", END)
    return builder.compile()


def extract_data(
    document: dict,
    record: dict,
    schema: dict | None,
    llm: Any,
) -> tuple[Resposta[ExtractionResult], dict]:
    """Run the extraction graph. Returns (envelope, metrics)."""
    grafo = build_extraction_graph()
    inicio = time.perf_counter()

    schema_obj = carregar_schema(schema)
    s0: ExtractionState = {
        "protocolo": {},
        "document": document,
        "record": record,
        "schema": schema_obj.model_dump() if schema else None,
        "cells": [],
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
        r = ExtractionResult(schema_version=schema_obj.version)
        metricas = {"latencia_s": round(lat, 2), "alertas": [f"GraphError: {e}"]}
        resp = Resposta(resultado=r, degradado=True, motivo_degradacao=str(e), alertas=[str(e)])
        return resp, metricas

    lat = time.perf_counter() - inicio
    resultado_dict = sf.get("resultado", {})
    resultado = ExtractionResult.model_validate(resultado_dict)
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
