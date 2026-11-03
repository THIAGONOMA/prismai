from __future__ import annotations

from enum import Enum


class TipoErro(str, Enum):
    FALSO_NEGATIVO = "falso_negativo"
    EVIDENCIA_FABRICADA = "evidencia_fabricada"
    CONFIANCA_DESCALIBRADA = "confianca_descalibrada"
    MOTIVO_AUSENTE = "motivo_ausente"
    FALSO_POSITIVO = "falso_positivo"
    ABSTENCAO_INDEVIDA = "abstencao_indevida"


PESOS_ERRO: dict[TipoErro, int] = {
    TipoErro.FALSO_NEGATIVO: 5,
    TipoErro.EVIDENCIA_FABRICADA: 4,
    TipoErro.CONFIANCA_DESCALIBRADA: 3,
    TipoErro.MOTIVO_AUSENTE: 3,
    TipoErro.FALSO_POSITIVO: 2,
    TipoErro.ABSTENCAO_INDEVIDA: 1,
}


def classificar_erro(resultado_exec: dict) -> list[TipoErro] | None:
    if resultado_exec.get("aprovado") is None:
        return None
    if resultado_exec.get("aprovado"):
        return None

    erros: list[TipoErro] = []

    if not resultado_exec.get("decisao_correta", True):
        esp, dec = resultado_exec.get("esperado"), resultado_exec.get("decision")
        if esp == "include" and dec in ("exclude", "uncertain"):
            erros.append(TipoErro.FALSO_NEGATIVO)
        elif esp == "exclude" and dec == "include":
            erros.append(TipoErro.FALSO_POSITIVO)
        elif esp == "uncertain" and dec != "uncertain":
            erros.append(TipoErro.ABSTENCAO_INDEVIDA)

    ev = resultado_exec.get("evidencia_fiel")
    if ev is not None and ev < 1.0:
        erros.append(TipoErro.EVIDENCIA_FABRICADA)

    if not resultado_exec.get("motivos_presentes", True):
        erros.append(TipoErro.MOTIVO_AUSENTE)

    if not erros:
        erros.append(TipoErro.ABSTENCAO_INDEVIDA)

    return erros


def dano_ponderado(resultados_exec: list[dict]) -> dict:
    dano_total, dano_maximo = 0, 0
    for r in resultados_exec:
        if r.get("aprovado") is None:
            continue
        dano_maximo += PESOS_ERRO[TipoErro.FALSO_NEGATIVO]
        erros = classificar_erro(r)
        if erros:
            dano_total += max(PESOS_ERRO.get(e, 1) for e in erros)

    qualidade = 1 - (dano_total / dano_maximo) if dano_maximo > 0 else 1.0
    return {
        "dano_total": dano_total,
        "dano_maximo": dano_maximo,
        "qualidade_ponderada": round(qualidade, 4),
    }
