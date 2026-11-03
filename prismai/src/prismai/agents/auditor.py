from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from prismai.agents.resilience import com_retry, parse_json_resposta
from prismai.core.models import ScreeningResult
from prismai.tools.literal import localizar_trecho_literal

_SKILL_PATH = Path(__file__).parent / "skills" / "auditar_evidencia.md"
_SKILL_CACHE: str | None = None

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


def agente_auditor(
    triador_output: dict,
    registro: dict,
    llm: Any,
    alertas_out: list[str] | None = None,
) -> tuple[ScreeningResult, dict, bool]:
    if alertas_out is None:
        alertas_out = []
    skill = _skill()
    trace: dict[str, Any] = {
        "agente": "auditor",
        "tipo": "agente",
        "skill": "auditar_evidencia",
        "chamadas_llm": 0,
        "chamadas_ferramentas": 0,
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "tools": [],
        "retries": 0,
        "ev_total": 0,
        "ev_encontradas": 0,
        "ev_parciais": 0,
    }

    documento = registro["titulo"] + " " + registro["abstract"]
    candidatas = triador_output.get("evidence", [])
    validadas: list[str] = []
    parciais: list[str] = []
    for ev in candidatas:
        inicio_t = time.perf_counter()
        loc = localizar_trecho_literal(documento, ev)
        lat_t = time.perf_counter() - inicio_t
        parcial = bool(loc.get("parcial", False))
        trace["chamadas_ferramentas"] += 1
        trace["ev_total"] += 1
        trace["tools"].append({
            "nome": "localizar_trecho_literal",
            "latencia_s": round(lat_t, 4),
            "consulta": ev[:60],
            "encontrado": loc["encontrado"],
            "parcial": parcial,
        })
        if loc["encontrado"]:
            trace["ev_encontradas"] += 1
            if parcial:
                trace["ev_parciais"] += 1
                parciais.append(loc["trecho"][:300])
            else:
                validadas.append(loc["trecho"][:300])

    if triador_output.get("decision") == "uncertain":
        resultado = ScreeningResult(
            decision="uncertain",
            reasons=triador_output.get("reasons", ["Insuficiente."]),
            evidence=[],
            confidence="low",
        )
        trace["latencia_s"] = round(sum(t["latencia_s"] for t in trace["tools"]), 2) if trace["tools"] else 0.0
        return resultado, trace, False

    prompt = (
        f"DECISAO DO TRIADOR: {triador_output.get('decision')}\n"
        f"MOTIVOS: {json.dumps(triador_output.get('reasons', []), ensure_ascii=False)}\n"
        f"EVIDENCIAS CANDIDATAS: {json.dumps(candidatas, ensure_ascii=False)}\n"
        f"EVIDENCIAS VALIDADAS (casamento exato): {json.dumps(validadas, ensure_ascii=False)}\n"
        f"EVIDENCIAS PARCIAIS (posicao estimada, NAO sao ancora verificada): "
        f"{json.dumps(parciais, ensure_ascii=False)}\n\nScreeningResult final."
    )
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
        alertas_out.append("DEGRADADO: Auditor falhou apos retries")
        resultado = ScreeningResult(
            decision=triador_output.get("decision", "uncertain"),
            reasons=triador_output.get("reasons", []),
            evidence=validadas,
            confidence="medium",
        )
        trace["latencia_s"] = round(sum(t["latencia_s"] for t in trace["tools"]), 2)
        return resultado, trace, True
    except Exception as e:
        alertas_out.append(f"DEGRADADO: Auditor falhou ({type(e).__name__})")
        resultado = ScreeningResult(
            decision=triador_output.get("decision", "uncertain"),
            reasons=triador_output.get("reasons", []),
            evidence=validadas,
            confidence="medium",
        )
        trace["latencia_s"] = round(sum(t["latencia_s"] for t in trace["tools"]), 2)
        return resultado, trace, True

    trace["latencia_s"] = round(sum(t["latencia_s"] for t in trace["tools"]) + lat_llm, 2)

    for tentativa_parse in range(2):
        try:
            resultado = parse_json_resposta(resp.content, ScreeningResult)
            return resultado, trace, False
        except (json.JSONDecodeError, ValueError, KeyError):
            if tentativa_parse == 0:
                try:
                    resp = com_retry(_invoke, transient_errors=TRANSIENT_ERRORS, trace=trace)
                    trace["chamadas_llm"] += 1
                except Exception:
                    break
            else:
                break

    alertas_out.append("DEGRADADO: Auditor — saida invalida, usando dados do triador")
    resultado = ScreeningResult(
        decision=triador_output.get("decision", "uncertain"),
        reasons=triador_output.get("reasons", []),
        evidence=validadas,
        confidence="medium",
    )
    return resultado, trace, True
