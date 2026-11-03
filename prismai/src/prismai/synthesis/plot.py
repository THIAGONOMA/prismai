"""Pure data builders and optional PNG renderers for forest & funnel plots."""
from __future__ import annotations

import math


def forest_data(study_effects: list[dict], pooled: dict, measure: str) -> dict:
    """Build pure-data structure for forest plot rendering."""
    studies = []
    for e in study_effects:
        if e.get("yi") is None:
            continue
        studies.append({
            "label": e.get("record_id", ""),
            "yi": e["yi"],
            "ci_low": e.get("ci_low"),
            "ci_high": e.get("ci_high"),
            "weight": e.get("weight_random") or e.get("weight_fixed"),
            "incluido": e.get("incluido", True),
        })
    return {
        "studies": studies,
        "pooled": {
            "yi": pooled.get("pooled_effect"),
            "ci_low": pooled.get("ci_low"),
            "ci_high": pooled.get("ci_high"),
        },
        "measure": measure,
        "model": pooled.get("model", "random"),
        "i2": pooled.get("i2"),
        "tau2": pooled.get("tau2"),
    }


def funnel_data_for_plot(efeitos: list[dict], pooled: float) -> dict:
    """Build pure-data structure for funnel plot rendering."""
    points = []
    for e in efeitos:
        if e.get("yi") is None or e.get("vi") is None:
            continue
        points.append({"yi": e["yi"], "se": math.sqrt(e["vi"])})
    return {"points": points, "pooled": pooled}


def render_forest_png(data: dict, path: str) -> str:
    """Render forest plot PNG. Requires matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError("matplotlib é necessário para renderizar plots: pip install matplotlib") from exc

    studies = data.get("studies", [])
    if not studies:
        return path

    fig, ax = plt.subplots(figsize=(8, max(3, len(studies) * 0.4 + 1)))
    labels = []
    for i, s in enumerate(studies):
        y_pos = len(studies) - 1 - i
        yi = s["yi"]
        lo = s.get("ci_low", yi)
        hi = s.get("ci_high", yi)
        ax.plot([lo, hi], [y_pos, y_pos], "b-", linewidth=1)
        ax.plot(yi, y_pos, "bs", markersize=5)
        labels.append(s.get("label", f"Study {i + 1}"))

    p = data.get("pooled", {})
    if p.get("yi") is not None:
        ax.axvline(p["yi"], color="red", linestyle="--", linewidth=0.8)
        diamond_y = -0.5
        ax.plot(p["yi"], diamond_y, "rD", markersize=8)

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel(data.get("measure", "Effect"))
    ax.axvline(0, color="gray", linestyle=":", linewidth=0.5)
    ax.set_title(f"Forest Plot (I²={data.get('i2', 0):.1f}%)")
    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def render_funnel_png(data: dict, path: str) -> str:
    """Render funnel plot PNG. Requires matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError("matplotlib é necessário para renderizar plots: pip install matplotlib") from exc

    points = data.get("points", [])
    pooled = data.get("pooled", 0)

    fig, ax = plt.subplots(figsize=(6, 5))
    if points:
        xs = [p["yi"] for p in points]
        ys = [p["se"] for p in points]
        ax.scatter(xs, ys, c="blue", s=20, zorder=3)
    ax.axvline(pooled, color="red", linestyle="--", linewidth=0.8)
    ax.invert_yaxis()
    ax.set_xlabel("Effect Size")
    ax.set_ylabel("Standard Error")
    ax.set_title("Funnel Plot")
    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
