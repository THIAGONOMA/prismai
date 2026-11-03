"""Deterministic impact detector for living reviews."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ImpactDetail(BaseModel):
    outcome_key: str
    tipo: str
    descricao: str
    antes: float | None = None
    depois: float | None = None


class ImpactResult(BaseModel):
    impacto: bool = False
    detalhes: list[ImpactDetail] = Field(default_factory=list)


def detectar_impacto(
    syntheses_antes: list[dict],
    syntheses_depois: list[dict],
    grade_antes: list[dict] | None = None,
    grade_depois: list[dict] | None = None,
) -> ImpactResult:
    """Compare pooled results before and after new studies.

    Detects:
    - Direction change: sign of pooled effect flipped
    - Significance change: p crossed 0.05 in either direction
    - GRADE certainty change: upgrade or downgrade
    - Substantial I² change: heterogeneity shifted > 25 percentage points
    """
    antes_by_key = {s["outcome_key"]: s for s in syntheses_antes}
    depois_by_key = {s["outcome_key"]: s for s in syntheses_depois}

    grade_antes_by_key = {g["outcome_key"]: g for g in (grade_antes or [])}
    grade_depois_by_key = {g["outcome_key"]: g for g in (grade_depois or [])}

    detalhes: list[ImpactDetail] = []

    all_keys = set(antes_by_key) | set(depois_by_key)
    for key in sorted(all_keys):
        a = antes_by_key.get(key)
        d = depois_by_key.get(key)
        if not a or not d:
            if d and not a:
                detalhes.append(ImpactDetail(
                    outcome_key=key, tipo="novo_desfecho",
                    descricao=f"Desfecho '{key}' apareceu com novos estudos",
                ))
            continue

        effect_a = a.get("pooled_effect")
        effect_d = d.get("pooled_effect")
        if effect_a is not None and effect_d is not None:
            if (effect_a > 0) != (effect_d > 0) and effect_a != 0 and effect_d != 0:
                detalhes.append(ImpactDetail(
                    outcome_key=key, tipo="mudanca_direcao",
                    descricao=f"Direção do efeito inverteu ({effect_a:.3f} -> {effect_d:.3f})",
                    antes=effect_a, depois=effect_d,
                ))

        p_a = a.get("p_value")
        p_d = d.get("p_value")
        if p_a is not None and p_d is not None:
            sig_a = p_a < 0.05
            sig_d = p_d < 0.05
            if sig_a != sig_d:
                direcao = "significativo -> não significativo" if sig_a else "não significativo -> significativo"
                detalhes.append(ImpactDetail(
                    outcome_key=key, tipo="mudanca_significancia",
                    descricao=f"Significância mudou: {direcao} (p: {p_a:.4f} -> {p_d:.4f})",
                    antes=p_a, depois=p_d,
                ))

        i2_a = a.get("i2")
        i2_d = d.get("i2")
        if i2_a is not None and i2_d is not None:
            if abs(i2_d - i2_a) > 25.0:
                detalhes.append(ImpactDetail(
                    outcome_key=key, tipo="mudanca_heterogeneidade",
                    descricao=f"I² mudou substancialmente ({i2_a:.1f}% -> {i2_d:.1f}%)",
                    antes=i2_a, depois=i2_d,
                ))

        ga = grade_antes_by_key.get(key)
        gd = grade_depois_by_key.get(key)
        if ga and gd:
            cert_a = ga.get("final_certainty", "")
            cert_d = gd.get("final_certainty", "")
            if cert_a and cert_d and cert_a != cert_d:
                detalhes.append(ImpactDetail(
                    outcome_key=key, tipo="mudanca_certeza",
                    descricao=f"Certeza GRADE mudou: {cert_a} -> {cert_d}",
                ))

    return ImpactResult(
        impacto=len(detalhes) > 0,
        detalhes=detalhes,
    )
