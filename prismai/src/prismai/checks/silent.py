from prismai.text.normalize import normalizar


def verificar_escopo(resultado, registro: dict) -> dict:
    """Check if reasons/evidence mention terms from the registro."""
    texto_reg = normalizar(registro["titulo"] + " " + registro["abstract"])
    tokens_reg = set(texto_reg.split())
    conteudo_resp = normalizar(" ".join(resultado.reasons) + " " + " ".join(resultado.evidence))
    tokens_resp = set(conteudo_resp.split())
    if not tokens_resp:
        return {"escopo_ok": True, "sobreposicao": 0.0, "nota": "Sem conteudo para verificar"}
    sobrep = len(tokens_resp & tokens_reg) / len(tokens_resp)
    return {"escopo_ok": sobrep >= 0.15, "sobreposicao": round(sobrep, 3)}


def verificar_calibracao(resultado, ev_fiel_score: float | None) -> dict:
    """Detect incoherence: high confidence with weak or absent evidence."""
    alertas: list[str] = []
    if resultado.confidence == "high":
        if not resultado.evidence:
            alertas.append("CALIBRACAO: confidence=high mas evidence=[]")
        if ev_fiel_score is not None and ev_fiel_score < 1.0:
            alertas.append(f"CALIBRACAO: confidence=high mas ev_fiel={ev_fiel_score}")
    if resultado.confidence == "low" and resultado.evidence and ev_fiel_score == 1.0:
        alertas.append("CALIBRACAO: confidence=low com evidencias validas — possivelmente subconfiante")
    return {"calibrado": len(alertas) == 0, "alertas": alertas}
