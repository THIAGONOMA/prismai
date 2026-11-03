from prismai.core.models import ScreeningResult
from prismai.tools.literal import localizar_trecho_literal


def auditor_deterministico(triador_output: dict, registro: dict) -> ScreeningResult:
    """Deterministic auditor: validates evidence without LLM call."""
    documento = registro["titulo"] + " " + registro["abstract"]
    candidatas = triador_output.get("evidence", [])
    validadas = []
    n_parciais = 0
    for ev in candidatas:
        loc = localizar_trecho_literal(documento, ev)
        if not loc["encontrado"]:
            continue
        if loc.get("parcial"):
            n_parciais += 1
            continue
        validadas.append(loc["trecho"][:300])
    decision = triador_output.get("decision", "uncertain")
    reasons = triador_output.get("reasons", [])
    confidence = triador_output.get("confidence", "medium")
    if decision == "uncertain":
        return ScreeningResult(decision="uncertain", reasons=reasons, evidence=[], confidence="low")
    ev_ratio = len(validadas) / len(candidatas) if candidatas else 1.0
    if ev_ratio < 0.5 and confidence == "high":
        confidence = "medium"
    if not validadas and n_parciais and confidence == "high":
        confidence = "medium"
    if not validadas and decision == "include":
        confidence = "medium" if confidence == "high" else confidence
    return ScreeningResult(decision=decision, reasons=reasons, evidence=validadas, confidence=confidence)
