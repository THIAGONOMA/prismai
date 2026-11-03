from prismai.core.models import ScreeningResult
from prismai.text.normalize import casa_termo, normalizar

PALAVRAS_CRITERIO = {
    "população": [
        "populacao", "graduacao", "undergraduate", "ensino medio", "profission", "corporativ", "vendas",
    ],
    "intervenção": [
        "intervencao", "llm", "language model", "chatbot", "gpt",
        "tutoria humana", "tutoria presencial", "humano", "ia", "inteligencia artificial",
    ],
    "desfecho": [
        "desfecho", "desempenho", "nota", "score", "grade", "gpa",
        "aprovacao", "retencao", "satisfacao", "percepcao", "outcome", "performance",
    ],
    "desenho": [
        "desenho", "editorial", "opiniao", "revisao", "meta-analise",
        "carta", "empirico", "experimental", "design",
    ],
}


def decisao_correta(resultado: ScreeningResult, esperado: str, aceitos: list[str] | None = None) -> bool:
    if resultado.decision == esperado:
        return True
    return bool(aceitos) and resultado.decision in aceitos


def evidencia_fiel(resultado: ScreeningResult, registro: dict) -> float | None:
    if not resultado.evidence:
        return None
    texto = normalizar(registro["titulo"] + " " + registro["abstract"])
    return round(
        sum(1 for e in resultado.evidence if normalizar(e) in texto) / len(resultado.evidence), 2
    )


def incerto_coerente(resultado: ScreeningResult) -> bool:
    if resultado.decision != "uncertain":
        return True
    return resultado.confidence == "low" and len(resultado.evidence) == 0


def motivos_presentes(resultado: ScreeningResult) -> bool:
    return any(m.strip() for m in resultado.reasons)


def desfecho_respeitado(resultado: ScreeningResult, caso: dict) -> bool | None:
    if caso.get("tem_desfecho_academico") is not False:
        return None
    return resultado.decision != "include"


def motivo_alinhado(
    resultado: ScreeningResult, criterios_violados: list[str] | None
) -> float | None:
    if not criterios_violados:
        return None
    mn = normalizar(" ".join(resultado.reasons))
    return round(
        sum(
            1 for c in criterios_violados if any(casa_termo(mn, p) for p in PALAVRAS_CRITERIO.get(c, []))
        )
        / len(criterios_violados),
        2,
    )


def avaliar(caso: dict, resultado: ScreeningResult, registro: dict) -> dict:
    if caso["verificacao"] == "manual":
        return {
            "aprovado": None,
            "evidencia_fiel": evidencia_fiel(resultado, registro),
            "incerto_coerente": incerto_coerente(resultado),
            "motivo_alinhado": None,
        }

    dec_ok = decisao_correta(resultado, caso["esperado"], caso.get("aceitos"))
    ev = evidencia_fiel(resultado, registro)
    ic = incerto_coerente(resultado)
    ma = motivo_alinhado(resultado, caso.get("criterio_violado"))
    mp = motivos_presentes(resultado)
    dr = desfecho_respeitado(resultado, caso)

    ap = dec_ok and ic
    if ev is not None and ev < 1.0:
        ap = False

    ap_est = ap and mp
    if dr is not None and not dr:
        ap_est = False

    return {
        "aprovado": ap,
        "aprovado_estrito": ap_est,
        "decisao_correta": dec_ok,
        "evidencia_fiel": ev,
        "incerto_coerente": ic,
        "motivo_alinhado": ma,
        "motivos_presentes": mp,
        "desfecho_respeitado": dr,
    }
