"""Deterministic numeric consistency checks for extracted data."""
from __future__ import annotations

from datetime import datetime


def verificar_consistencia(cells: list[dict]) -> list[str]:
    """Check numeric cells for arithmetic/logical inconsistencies.

    Returns a list of human-readable flag strings (empty = all OK).
    """
    flags: list[str] = []
    by_field = {c["field"]: c.get("value") for c in cells}

    n_int = _to_num(by_field.get("n_intervencao"))
    n_ctrl = _to_num(by_field.get("n_controle"))
    n_total = _to_num(by_field.get("n_total"))
    if n_int is not None and n_ctrl is not None and n_total is not None:
        if abs((n_int + n_ctrl) - n_total) > 0:
            flags.append(
                f"n_intervencao ({n_int}) + n_controle ({n_ctrl}) != n_total ({n_total})"
            )

    dp_int = _to_num(by_field.get("dp_intervencao"))
    if dp_int is not None and dp_int <= 0:
        flags.append(f"dp_intervencao deve ser positivo, mas é {dp_int}")

    dp_ctrl = _to_num(by_field.get("dp_controle"))
    if dp_ctrl is not None and dp_ctrl <= 0:
        flags.append(f"dp_controle deve ser positivo, mas é {dp_ctrl}")

    ano = _to_num(by_field.get("ano_publicacao"))
    max_year = datetime.now().year + 1
    if ano is not None and (ano < 1900 or ano > max_year):
        flags.append(f"ano_publicacao ({int(ano)}) fora do intervalo plausível [1900, {max_year}]")

    valor_p = _to_num(by_field.get("valor_p"))
    if valor_p is not None and (valor_p < 0 or valor_p > 1):
        flags.append(f"valor_p ({valor_p}) fora do intervalo [0, 1]")

    ev_int = _to_num(by_field.get("eventos_intervencao"))
    if ev_int is not None and n_int is not None and ev_int > n_int:
        flags.append(
            f"eventos_intervencao ({int(ev_int)}) excede n_intervencao ({int(n_int)})"
        )

    ev_ctrl = _to_num(by_field.get("eventos_controle"))
    if ev_ctrl is not None and n_ctrl is not None and ev_ctrl > n_ctrl:
        flags.append(
            f"eventos_controle ({int(ev_ctrl)}) excede n_controle ({int(n_ctrl)})"
        )

    return flags


def _to_num(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
