"""Compute individual study effect sizes for meta-analysis."""
from __future__ import annotations

import math

from prismai.synthesis.dist import norm_ppf

_Z95 = -norm_ppf(0.025)  # ~1.96


def efeito_estudo(cells: dict, measure: str) -> dict:
    """Compute effect size from study-level extracted data.

    Returns dict with yi, vi, se, ci_low, ci_high, n_total. Or {erro: "..."}.
    """
    try:
        if measure == "smd":
            return _smd(cells)
        if measure == "md":
            return _md(cells)
        if measure == "rr":
            return _rr(cells)
        if measure == "or":
            return _or(cells)
        return {"erro": f"Medida desconhecida: {measure}"}
    except (KeyError, TypeError, ValueError) as e:
        return {"erro": str(e)}


def _require(cells: dict, *keys: str) -> list:
    vals = []
    for k in keys:
        v = cells.get(k)
        if v is None:
            raise KeyError(f"Campo obrigatório ausente: {k}")
        vals.append(float(v))
    return vals


def _smd(cells: dict) -> dict:
    n1, n2, m1, sd1, m2, sd2 = _require(
        cells, "n_intervencao", "n_controle",
        "media_intervencao", "dp_intervencao", "media_controle", "dp_controle",
    )
    n1, n2 = int(n1), int(n2)
    df = n1 + n2 - 2
    if df <= 0:
        raise ValueError("df <= 0")
    sp = math.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / df)
    if sp == 0:
        raise ValueError("Pooled SD = 0")
    d = (m1 - m2) / sp
    j = 1.0 - 3.0 / (4.0 * df - 1.0)
    yi = j * d
    vi = j**2 * (n1 + n2) / (n1 * n2) + yi**2 / (2.0 * (n1 + n2))
    se = math.sqrt(vi)
    return {
        "yi": yi, "vi": vi, "se": se,
        "ci_low": yi - _Z95 * se, "ci_high": yi + _Z95 * se,
        "n_total": n1 + n2,
    }


def _md(cells: dict) -> dict:
    n1, n2, m1, sd1, m2, sd2 = _require(
        cells, "n_intervencao", "n_controle",
        "media_intervencao", "dp_intervencao", "media_controle", "dp_controle",
    )
    n1, n2 = int(n1), int(n2)
    yi = m1 - m2
    vi = sd1**2 / n1 + sd2**2 / n2
    se = math.sqrt(vi)
    return {
        "yi": yi, "vi": vi, "se": se,
        "ci_low": yi - _Z95 * se, "ci_high": yi + _Z95 * se,
        "n_total": n1 + n2,
    }


def _rr(cells: dict) -> dict:
    e1, n1, e2, n2 = _require(
        cells, "eventos_intervencao", "n_intervencao", "eventos_controle", "n_controle",
    )
    e1, n1, e2, n2 = int(e1), int(n1), int(e2), int(n2)
    cc = 0.0
    if e1 == 0 or e2 == 0 or e1 == n1 or e2 == n2:
        cc = 0.5
    e1c, n1c, e2c, n2c = e1 + cc, n1 + 2 * cc, e2 + cc, n2 + 2 * cc
    rr = (e1c / n1c) / (e2c / n2c)
    yi = math.log(rr)
    vi = 1.0 / e1c - 1.0 / n1c + 1.0 / e2c - 1.0 / n2c
    se = math.sqrt(vi)
    return {
        "yi": yi, "vi": vi, "se": se,
        "ci_low": yi - _Z95 * se, "ci_high": yi + _Z95 * se,
        "n_total": n1 + n2,
    }


def _or(cells: dict) -> dict:
    e1, n1, e2, n2 = _require(
        cells, "eventos_intervencao", "n_intervencao", "eventos_controle", "n_controle",
    )
    e1, n1, e2, n2 = int(e1), int(n1), int(e2), int(n2)
    a, b = e1, n1 - e1
    c, d = e2, n2 - e2
    cc = 0.0
    if a == 0 or b == 0 or c == 0 or d == 0:
        cc = 0.5
    a, b, c, d = a + cc, b + cc, c + cc, d + cc
    odds_r = (a * d) / (b * c)
    yi = math.log(odds_r)
    vi = 1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d
    se = math.sqrt(vi)
    return {
        "yi": yi, "vi": vi, "se": se,
        "ci_low": yi - _Z95 * se, "ci_high": yi + _Z95 * se,
        "n_total": n1 + n2,
    }
