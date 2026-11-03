"""Inter-rater agreement metrics for dual screening."""
from __future__ import annotations

from collections import Counter

_DISAGREEMENT_MATRIX: dict[tuple[str, str], float] = {
    ("include", "exclude"): 3.0,
    ("exclude", "include"): 3.0,
    ("include", "uncertain"): 2.0,
    ("uncertain", "include"): 2.0,
    ("exclude", "uncertain"): 1.0,
    ("uncertain", "exclude"): 1.0,
}


def disagreement_score(dec_a: str, dec_b: str) -> float:
    """Weighted disagreement aligned with error asymmetry (false negative = worst)."""
    if dec_a == dec_b:
        return 0.0
    return _DISAGREEMENT_MATRIX.get((dec_a, dec_b), 1.0)


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Cohen's kappa: (po - pe) / (1 - pe). Returns 0.0 when pe == 1."""
    if len(labels_a) != len(labels_b):
        raise ValueError("Label lists must have the same length")
    n = len(labels_a)
    if n == 0:
        return 0.0

    po = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n

    count_a = Counter(labels_a)
    count_b = Counter(labels_b)
    categories = set(count_a) | set(count_b)
    pe = sum((count_a[c] / n) * (count_b[c] / n) for c in categories)

    if pe >= 1.0:
        return 0.0
    return (po - pe) / (1.0 - pe)
