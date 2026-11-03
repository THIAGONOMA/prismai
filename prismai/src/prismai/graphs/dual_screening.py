"""Dual screening: two independent screen_v4 runs with conflict detection."""
from __future__ import annotations

import asyncio
from typing import Any

from prismai.core.envelope import Resposta
from prismai.core.models import ScreeningResult
from prismai.eval.agreement import disagreement_score
from prismai.graphs.screening import screen_v4


async def screen_dual(
    registro: dict,
    protocolo: dict,
    llm_a: Any,
    llm_b: Any,
    llm_auditor_a: Any = None,
    llm_auditor_b: Any = None,
) -> tuple[Resposta[ScreeningResult], dict, Resposta[ScreeningResult], dict, dict | None]:
    """Run screen_v4 twice concurrently. Returns (resp_a, met_a, resp_b, met_b, conflict|None)."""
    resp_a, met_a = await asyncio.to_thread(screen_v4, registro, protocolo, llm_a, llm_auditor_a)
    resp_b, met_b = await asyncio.to_thread(screen_v4, registro, protocolo, llm_b, llm_auditor_b)

    # Intentionally sequential for now; gather causes issues with some LLM clients
    # that are not fully thread-safe. Can be parallelized later.

    dec_a = resp_a.resultado.decision
    dec_b = resp_b.resultado.decision

    conflict = None
    if dec_a != dec_b:
        conflict = {
            "registro_id": registro["id"],
            "decision_a": dec_a,
            "decision_b": dec_b,
            "screener_a": "primary",
            "screener_b": "secondary",
            "disagreement_score": disagreement_score(dec_a, dec_b),
            "status": "pending",
        }

    return resp_a, met_a, resp_b, met_b, conflict
