from __future__ import annotations

import json
from typing import Any

from prismai.agents.resilience import parse_json_resposta
from prismai.text.normalize import normalizar

MARCADORES_INSUFICIENTE = [
    "no systematic data", "no data collected", "anecdotal", "no formal assessment",
    "no conclusions", "preliminary observations", "sem dados", "anedotico", "sem coleta sistematica",
]

MARCADORES_NAO_EMPIRICO = [
    "editorial", "opinion", "letter to the editor", "commentary", "review of",
    "meta-analysis", "systematic review",
]


_JULGAMENTO_SYSTEM = (
    "Você julga se um abstract tem informação empírica suficiente "
    "para triagem de revisão sistemática.\n\n"
    "Responda SOMENTE JSON:\n"
    '{"suficiente": true ou false, "tipo_insuficiencia": null ou '
    '"dados_insuficientes" ou "nao_empirico" ou "vazio", "motivo": "..."}\n\n'
    "Critério: o texto reporta alguma medição, contagem ou comparação?\n"
    "- Editorial, opinião ou comentário sem dados de um estudo: "
    'suficiente=false, tipo_insuficiencia="nao_empirico".\n'
    "- Relato de impressões, sem nada medido nem comparado: "
    'suficiente=false, tipo_insuficiencia="dados_insuficientes".\n'
    "- Estudo empírico com medição, mesmo que mencione relatos anedóticos "
    "de outros trabalhos ou diga que não conclui sobre um desfecho secundário: "
    "suficiente=true, tipo_insuficiencia=null.\n"
    '- Uma frase negada ("we draw no conclusions", "beyond anecdotal", '
    '"no conclusions about retention") NÃO torna o estudo insuficiente.\n\n'
    "A pista heurística abaixo é busca por substring e ignora negação. "
    "Não é confiável. Se ela contradisser o texto, ignore a pista."
)


def pista_heuristica(registro: dict) -> dict:
    abstract = registro.get("abstract", "")
    if not abstract.strip():
        return {
            "suficiente": False, "motivo": "Abstract vazio.",
            "marcadores": [], "tipo_insuficiencia": "vazio", "n_palavras": 0,
        }
    texto_norm = normalizar(registro.get("titulo", "") + (" " + abstract))
    marc: list[tuple[str, str]] = []
    for m in MARCADORES_INSUFICIENTE:
        if normalizar(m) in texto_norm:
            marc.append(("insuficiente", m))
    for m in MARCADORES_NAO_EMPIRICO:
        if normalizar(m) in texto_norm:
            marc.append(("nao_empirico", m))
    n = len(abstract.split())
    if n < 30 and not marc:
        marc.append(("insuficiente", f"abstract curto ({n} palavras)"))
    insuf = any(t == "insuficiente" for t, _ in marc)
    nao_emp = any(t == "nao_empirico" for t, _ in marc) and not insuf
    return {
        "suficiente": not insuf and not nao_emp,
        "motivo": "Marcadores detectados." if marc else "Texto suficiente.",
        "marcadores": [m for _, m in marc],
        "tipo_insuficiencia": "dados_insuficientes" if insuf else ("nao_empirico" if nao_emp else None),
        "n_palavras": n,
    }


def julgar_suficiencia(registro: dict, llm: Any, pista: dict) -> dict:
    from langchain_core.messages import HumanMessage, SystemMessage

    prompt = (
        f"TITULO: {registro.get('titulo', '')}\n"
        f"ABSTRACT: {registro.get('abstract', '')}\n\n"
        "PISTA HEURISTICA (nao confiavel):\n"
        f"suficiente={pista.get('suficiente')}, tipo={pista.get('tipo_insuficiencia')}, "
        f"marcadores={pista.get('marcadores')}"
    )
    resp = llm.invoke([SystemMessage(content=_JULGAMENTO_SYSTEM), HumanMessage(content=prompt)])
    content = resp.content if hasattr(resp, "content") else str(resp)
    dados = parse_json_resposta(content)
    if not isinstance(dados, dict) or "suficiente" not in dados:
        raise ValueError("julgamento de suficiencia sem campo suficiente")
    return {
        "suficiente": bool(dados["suficiente"]),
        "motivo": str(dados.get("motivo") or ""),
        "marcadores": pista.get("marcadores", []),
        "tipo_insuficiencia": dados.get("tipo_insuficiencia"),
        "n_palavras": pista.get("n_palavras", 0),
    }


def avaliar_suficiencia(registro: dict, protocolo: dict, llm: Any = None) -> dict:
    del protocolo  # o julgamento olha o texto, não os critérios PICO
    pista = pista_heuristica(registro)
    if llm is None:
        return {**pista, "fonte": "heuristica", "confiavel": False}
    try:
        julgamento = julgar_suficiencia(registro, llm, pista)
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        return {**pista, "fonte": "heuristica", "confiavel": False}
    return {**julgamento, "fonte": "llm", "confiavel": True, "pista_heuristica": pista}
