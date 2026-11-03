from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from prismai.agents.resilience import com_retry, parse_json_resposta
from prismai.tools.sufficiency import avaliar_suficiencia

_SKILL_PATH = Path(__file__).parent / "skills" / "triar_pico.md"
_SKILL_CACHE: str | None = None

TIMEOUT_LLM_S = 60

TRANSIENT_ERRORS: tuple[type[Exception], ...] = (TimeoutError,)
try:
    from openai import APIConnectionError, APITimeoutError, RateLimitError

    TRANSIENT_ERRORS = (*TRANSIENT_ERRORS, RateLimitError, APIConnectionError, APITimeoutError)
except ImportError:
    pass
try:
    from anthropic import APIConnectionError as AnthConnectionError
    from anthropic import APITimeoutError as AnthTimeoutError
    from anthropic import RateLimitError as AnthRateLimitError

    TRANSIENT_ERRORS = (*TRANSIENT_ERRORS, AnthRateLimitError, AnthConnectionError, AnthTimeoutError)
except ImportError:
    pass


def _skill() -> str:
    global _SKILL_CACHE  # noqa: PLW0603
    if _SKILL_CACHE is None:
        _SKILL_CACHE = _SKILL_PATH.read_text(encoding="utf-8")
    return _SKILL_CACHE


def _formatar_protocolo(protocolo: dict) -> str:
    if hasattr(protocolo, "formatar"):
        return protocolo.formatar()
    return (
        f"PERGUNTA DE PESQUISA: {protocolo['pergunta']}\n"
        f"P (População): {protocolo['P']}\nI (Intervenção): {protocolo['I']}\n"
        f"C (Comparação): {protocolo['C']}\nO (Desfecho): {protocolo['O']}\n"
        f"Desenho aceito: {protocolo['desenho']}\n"
        f"Critérios de inclusão: {'; '.join(protocolo['inclusao'])}\n"
        f"Critérios de exclusão: {'; '.join(protocolo['exclusao'])}"
    )


def agente_triador(
    registro: dict,
    protocolo: dict,
    llm: Any,
    alertas_out: list[str] | None = None,
) -> tuple[dict, dict, bool]:
    if alertas_out is None:
        alertas_out = []
    skill = _skill()
    trace: dict[str, Any] = {
        "agente": "triador",
        "tipo": "agente",
        "skill": "triar_pico",
        "chamadas_llm": 0,
        "chamadas_ferramentas": 0,
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "tools": [],
        "retries": 0,
    }

    inicio_suf = time.perf_counter()
    suf = avaliar_suficiencia(registro, protocolo, llm)
    lat_suf = time.perf_counter() - inicio_suf
    trace["chamadas_ferramentas"] += 1
    trace["tools"].append({
        "nome": "avaliar_suficiencia",
        "latencia_s": round(lat_suf, 4),
        "resultado": {"suficiente": suf["suficiente"], "tipo": suf.get("tipo_insuficiencia")},
    })

    texto = f"TITULO: {registro['titulo']}\nABSTRACT: {registro['abstract']}"
    suf_info = (
        f"\n\nINFORMACAO DE SUFICIENCIA (julgamento, fonte={suf.get('fonte')}):\n"
        f"suficiente={suf['suficiente']}, tipo={suf.get('tipo_insuficiencia')}, "
        f"motivo={suf.get('motivo')}\n"
    )
    pista = suf.get("pista_heuristica")
    if pista:
        suf_info += (
            "PISTA HEURISTICA (nao confiavel; busca por substring ignora negacao): "
            f"suficiente={pista['suficiente']}, marcadores={pista['marcadores']}\n"
        )
    suf_info += "NOTA: use para calibrar, mas a DECISAO e sua."
    prompt = f"PROTOCOLO:\n{_formatar_protocolo(protocolo)}\n\nREGISTRO:\n{texto}{suf_info}"
    mensagens = [SystemMessage(content=skill), HumanMessage(content=prompt)]

    def _invoke():
        return llm.invoke(mensagens)

    try:
        inicio_llm = time.perf_counter()
        resp = com_retry(_invoke, transient_errors=TRANSIENT_ERRORS, trace=trace)
        lat_llm = time.perf_counter() - inicio_llm
        uso = getattr(resp, "usage_metadata", None) or {}
        trace["chamadas_llm"] += 1
        trace["tokens_entrada"] += uso.get("input_tokens") or 0
        trace["tokens_saida"] += uso.get("output_tokens") or 0
    except TRANSIENT_ERRORS if TRANSIENT_ERRORS else () as _:
        alertas_out.append("DEGRADADO: Triador falhou apos retries (transitoria)")
        trace["latencia_s"] = round(time.perf_counter() - inicio_suf, 2)
        return (
            {"decision": "uncertain", "reasons": ["Erro transitorio no triador."], "evidence": [], "confidence": "low"},
            trace,
            True,
        )
    except Exception as e:
        alertas_out.append(f"DEGRADADO: Triador falhou ({type(e).__name__})")
        trace["latencia_s"] = round(time.perf_counter() - inicio_suf, 2)
        return (
            {"decision": "uncertain", "reasons": [f"Erro: {type(e).__name__}"], "evidence": [], "confidence": "low"},
            trace,
            True,
        )

    trace["latencia_s"] = round(lat_suf + lat_llm, 2)

    for tentativa_parse in range(2):
        try:
            dados = parse_json_resposta(resp.content)
            for campo in ("decision", "reasons", "evidence", "confidence"):
                if campo not in dados:
                    raise ValueError(f"Campo '{campo}' ausente na saida do triador")
            return dados, trace, False
        except (json.JSONDecodeError, ValueError, KeyError):
            if tentativa_parse == 0:
                try:
                    resp = com_retry(_invoke, transient_errors=TRANSIENT_ERRORS, trace=trace)
                    trace["chamadas_llm"] += 1
                except Exception:
                    break
            else:
                break

    alertas_out.append("DEGRADADO: Triador — saida invalida apos repeticao")
    return (
        {
            "decision": "uncertain",
            "reasons": ["Erro parse triador (v4: validacao falhou)."],
            "evidence": [],
            "confidence": "low",
        },
        trace,
        True,
    )
