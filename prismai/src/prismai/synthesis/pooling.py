"""Fixed and random-effects meta-analytic pooling (DerSimonian-Laird)."""
from __future__ import annotations

import math

from prismai.synthesis.dist import chi2_sf, norm_ppf, norm_sf, t_sf

_Z95 = -norm_ppf(0.025)


def agrupar(efeitos: list[dict], model: str = "random") -> dict:
    """Pool study effects using fixed or random (DL) model.

    Each effect dict must have 'yi' and 'vi' keys.
    Returns pooled statistics dict.
    """
    valid = [e for e in efeitos if e.get("yi") is not None and e.get("vi") is not None and e["vi"] > 0]
    k = len(valid)
    if k == 0:
        return {"pooled_effect": None, "se": None, "k": 0}

    ys = [e["yi"] for e in valid]
    vs = [e["vi"] for e in valid]

    # Fixed-effect weights
    w_fixed = [1.0 / v for v in vs]
    sum_w = sum(w_fixed)
    pooled_fixed = sum(w * y for w, y in zip(w_fixed, ys)) / sum_w
    se_fixed = 1.0 / math.sqrt(sum_w)

    # Cochran's Q
    q_val = sum(w * (y - pooled_fixed) ** 2 for w, y in zip(w_fixed, ys))
    q_df = max(k - 1, 1)
    q_p = chi2_sf(q_val, q_df) if k > 1 else 1.0

    # DerSimonian-Laird tau^2
    c_val = sum_w - sum(w**2 for w in w_fixed) / sum_w
    tau2 = max(0.0, (q_val - (k - 1)) / c_val) if c_val > 0 else 0.0

    # I^2
    i2 = max(0.0, (q_val - (k - 1)) / q_val * 100.0) if q_val > 0 else 0.0

    if model == "fixed" or tau2 == 0:
        pooled = pooled_fixed
        se_pooled = se_fixed
        weights = [w / sum_w for w in w_fixed]
    else:
        w_random = [1.0 / (v + tau2) for v in vs]
        sum_wr = sum(w_random)
        pooled = sum(w * y for w, y in zip(w_random, ys)) / sum_wr
        se_pooled = 1.0 / math.sqrt(sum_wr)
        weights = [w / sum_wr for w in w_random]

    z_val = pooled / se_pooled if se_pooled > 0 else 0.0
    p_value = 2.0 * norm_sf(abs(z_val))

    # Prediction interval (t distribution with k-2 df)
    prediction_low = None
    prediction_high = None
    if k >= 3 and tau2 > 0:
        t_crit = -norm_ppf(0.025)  # approximate with normal for simplicity
        try:
            # Use exact t critical value for k-2 df
            t_crit_val = _find_t_crit(k - 2, 0.025)
        except Exception:
            t_crit_val = t_crit
        pred_se = math.sqrt(tau2 + se_pooled**2)
        prediction_low = pooled - t_crit_val * pred_se
        prediction_high = pooled + t_crit_val * pred_se

    return {
        "pooled_effect": pooled,
        "se": se_pooled,
        "ci_low": pooled - _Z95 * se_pooled,
        "ci_high": pooled + _Z95 * se_pooled,
        "z": z_val,
        "p_value": p_value,
        "tau2": tau2,
        "q": q_val,
        "q_p": q_p,
        "i2": i2,
        "prediction_low": prediction_low,
        "prediction_high": prediction_high,
        "k": k,
        "weights": weights,
    }


def _find_t_crit(df: int, alpha: float) -> float:
    """Find t critical value via bisection."""
    lo, hi = 0.0, 20.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if t_sf(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0
