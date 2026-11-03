"""Deterministic GRADE domain assessments."""
from __future__ import annotations

_CERTAINTY_MAP = {4: "high", 3: "moderate", 2: "low", 1: "very_low"}
_CERTAINTY_NUM = {"high": 4, "moderate": 3, "low": 2, "very_low": 1}


def avaliar_risco_vies(study_effects: list[dict]) -> tuple[int, str]:
    """Downgrade based on proportion of high-risk studies."""
    included = [s for s in study_effects if s.get("incluido", True)]
    if not included:
        return 0, "Nenhum estudo incluído"
    robs = [s.get("rob", "low") for s in included]
    n = len(robs)
    n_high = sum(1 for r in robs if r == "high")
    n_concerns = sum(1 for r in robs if r == "some_concerns")

    if n_high > n / 2:
        return -2, f"Mais de 50% dos estudos com alto risco de viés ({n_high}/{n})"
    if n_high > 0 or n_concerns > n / 2:
        return -1, f"Risco de viés presente: {n_high} alto, {n_concerns} alguma preocupação de {n}"
    return 0, f"Todos os {n} estudos com baixo risco de viés"


def avaliar_inconsistencia(i2: float | None, k: int) -> tuple[int, str]:
    """Downgrade based on I² heterogeneity statistic."""
    if k <= 1:
        return 0, "Apenas 1 estudo, inconsistência não avaliável"
    if i2 is None:
        return 0, "I² não disponível"
    if i2 > 75:
        return -2, f"Heterogeneidade muito alta (I²={i2:.1f}%)"
    if i2 >= 40:
        return -1, f"Heterogeneidade moderada a alta (I²={i2:.1f}%)"
    return 0, f"Heterogeneidade baixa (I²={i2:.1f}%)"


def avaliar_imprecisao(
    ci_low: float | None,
    ci_high: float | None,
    measure: str,
    mid: float | None,
    n_total: int | None,
) -> tuple[int, str]:
    """Downgrade based on CI width and optimal information size."""
    downgrades = 0
    reasons = []

    null_value = 0.0  # log scale for rr/or, absolute for smd/md

    if ci_low is not None and ci_high is not None:
        if ci_low <= null_value <= ci_high:
            downgrades += 1
            reasons.append("IC 95% cruza o valor nulo")

    if n_total is not None and n_total < 400:
        downgrades += 1
        reasons.append(f"Tamanho amostral insuficiente (n={n_total})")

    rating = min(downgrades, 2)
    justificativa = "; ".join(reasons) if reasons else "Precisão adequada"
    return -rating, justificativa


def avaliar_vies_publicacao(egger_p: float | None, k: int) -> tuple[int, str]:
    """Downgrade based on Egger's test for publication bias."""
    if k < 10:
        return 0, f"Teste de Egger não aplicável (k={k} < 10)"
    if egger_p is None:
        return 0, "Teste de Egger não disponível"
    if egger_p < 0.10:
        return -1, f"Assimetria significativa no funnel plot (p={egger_p:.3f})"
    return 0, f"Sem evidência de viés de publicação (p={egger_p:.3f})"


def certeza_final(inicial: str, ratings: list[int]) -> str:
    """Compute final GRADE certainty from starting level and domain ratings.

    RCT starts at 4 (high), observational at 2 (low). Sum clamped [1,4].
    """
    start_num = 4 if inicial == "high" else 2
    total = start_num + sum(ratings)
    clamped = max(1, min(4, total))
    return _CERTAINTY_MAP[clamped]
