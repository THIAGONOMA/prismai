"""Statistical stopping criterion for dual screening based on Wilson lower bound."""
from __future__ import annotations

from prismai.config import settings
from prismai.eval.stats import wilson


def should_stop(
    n_screened: int,
    n_agree: int,
    threshold: float | None = None,
    z: float = 1.96,
) -> dict:
    """Check whether agreement lower bound meets the threshold.

    Returns a dict with should_stop, lower_bound, upper_bound, agreement_rate,
    n_screened, and n_agree.
    """
    if threshold is None:
        threshold = settings.stopping_threshold
    min_sample = settings.stopping_min_sample

    if n_screened < min_sample:
        return {
            "should_stop": False,
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "agreement_rate": n_agree / n_screened if n_screened > 0 else 0.0,
            "n_screened": n_screened,
            "n_agree": n_agree,
            "reason": f"min_sample not reached ({n_screened}/{min_sample})",
        }

    lower, upper = wilson(n_agree, n_screened, z)

    return {
        "should_stop": lower >= threshold,
        "lower_bound": lower,
        "upper_bound": upper,
        "agreement_rate": round(n_agree / n_screened, 4) if n_screened > 0 else 0.0,
        "n_screened": n_screened,
        "n_agree": n_agree,
        "reason": "criterion_met" if lower >= threshold else "below_threshold",
    }
