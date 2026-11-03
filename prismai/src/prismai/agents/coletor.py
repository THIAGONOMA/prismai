from __future__ import annotations

import time
from typing import Any

from prismai.connectors.arxiv import buscar_arxiv


def agente_coletor(query: str, max_results: int = 3) -> tuple[list[dict], dict]:
    trace: dict[str, Any] = {
        "agente": "coletor",
        "tipo": "etapa_de_fluxo",
        "skill": "coletar_arxiv",
        "chamadas_llm": 0,
        "chamadas_ferramentas": 0,
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "tools": [],
    }
    inicio = time.perf_counter()
    resultados = buscar_arxiv(query, max_results)
    lat = time.perf_counter() - inicio
    trace["chamadas_ferramentas"] += 1
    trace["latencia_s"] = round(lat, 2)
    n_ok = sum(1 for r in resultados if "erro" not in r and r.get("titulo") and r.get("abstract"))
    trace["tools"].append({
        "nome": "buscar_arxiv",
        "latencia_s": round(lat, 4),
        "query": query,
        "n_resultados": len(resultados),
        "n_validos": n_ok,
    })
    return resultados, trace
