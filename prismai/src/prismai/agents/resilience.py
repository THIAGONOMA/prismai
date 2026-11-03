from __future__ import annotations

import json
import time
from typing import Any, Callable


def com_retry(
    fn: Callable[..., Any],
    *args: Any,
    max_tentativas: int = 3,
    base: float = 1.0,
    transient_errors: tuple[type[Exception], ...] = (),
    sleep_fn: Callable[[float], None] = time.sleep,
    trace: dict | None = None,
    **kwargs: Any,
) -> Any:
    """Call fn with exponential backoff on transient errors. sleep_fn is injectable for testing."""
    for tentativa in range(max_tentativas + 1):
        try:
            return fn(*args, **kwargs)
        except transient_errors as e:
            if tentativa < max_tentativas:
                espera = base * (2**tentativa)
                if trace is not None:
                    trace.setdefault("retries_log", []).append(
                        {"tentativa": tentativa + 1, "erro": type(e).__name__, "espera_s": espera}
                    )
                sleep_fn(espera)
                continue
            raise


def parse_json_resposta(texto_raw: str, schema_class: type | None = None) -> Any:
    """Parse JSON from LLM output, stripping markdown fences if present."""
    t = texto_raw.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    dados = json.loads(t)
    if schema_class:
        return schema_class(**dados)
    return dados
