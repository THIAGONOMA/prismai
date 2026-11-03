"""Publication bias diagnostics (Egger's test, funnel data)."""
from __future__ import annotations

import math

from prismai.synthesis.dist import t_sf


def egger_test(efeitos: list[dict]) -> dict:
    """Egger's regression test for funnel plot asymmetry.

    Requires k >= 10. Returns {intercept, se, t, p} or {not_evaluable: True, reason: ...}.
    """
    valid = [e for e in efeitos if e.get("yi") is not None and e.get("vi") is not None and e["vi"] > 0]
    k = len(valid)
    if k < 10:
        return {"not_evaluable": True, "reason": f"k={k} < 10, teste de Egger não aplicável"}

    # Egger: regress z_i = y_i / se_i on precision_i = 1/se_i
    ses = [math.sqrt(e["vi"]) for e in valid]
    x = [1.0 / s for s in ses]  # precision
    y_vals = [e["yi"] / s for e, s in zip(valid, ses)]  # standardized effect

    n = len(x)
    sx = sum(x)
    sy = sum(y_vals)
    sxx = sum(xi**2 for xi in x)
    sxy = sum(xi * yi for xi, yi in zip(x, y_vals))

    denom = n * sxx - sx**2
    if denom == 0:
        return {"not_evaluable": True, "reason": "Variância zero na regressão"}

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n

    # residual SE
    y_pred = [slope * xi + intercept for xi in x]
    ssr = sum((yi - yp) ** 2 for yi, yp in zip(y_vals, y_pred))
    mse = ssr / (n - 2) if n > 2 else 0.0
    se_intercept = math.sqrt(mse * sxx / denom) if mse > 0 and denom > 0 else 0.0

    t_val = intercept / se_intercept if se_intercept > 0 else 0.0
    p_val = 2.0 * t_sf(abs(t_val), n - 2) if n > 2 else 1.0

    return {"intercept": intercept, "se": se_intercept, "t": t_val, "p": p_val}


def funnel_data(efeitos: list[dict], pooled: float) -> list[dict]:
    """Prepare data points for funnel plot."""
    result = []
    for i, e in enumerate(efeitos):
        if e.get("yi") is None or e.get("vi") is None:
            continue
        se = math.sqrt(e["vi"])
        result.append({
            "yi": e["yi"],
            "se": se,
            "label": e.get("record_id", f"study_{i}"),
        })
    return result
