from prismai.text.normalize import normalizar


def localizar_trecho_literal(documento: str, consulta: str, janela: int = 15) -> dict:
    doc_norm = normalizar(documento)
    con_norm = normalizar(consulta)
    if con_norm in doc_norm:
        pos = doc_norm.index(con_norm)
        palavras = documento.split()
        acum = idx = 0
        for i, p in enumerate(palavras):
            if acum >= pos:
                idx = i
                break
            acum += len(p) + 1
        return {
            "encontrado": True,
            "trecho": " ".join(palavras[idx : min(len(palavras), idx + len(consulta.split()) + 4)]),
            "posicao": pos,
            "parcial": False,
        }
    tokens = con_norm.split()
    if len(tokens) >= 4:
        metade = len(tokens) // 2
        for sub in [tokens[: metade + 2], tokens[metade - 1 :]]:
            ss = " ".join(sub)
            if ss in doc_norm:
                pos = doc_norm.index(ss)
                palavras = documento.split()
                idx = max(0, min(pos // 6, len(palavras) - 1))
                return {
                    "encontrado": True,
                    "trecho": " ".join(palavras[max(0, idx - 3) : idx + 20]),
                    "posicao": pos,
                    "parcial": True,
                }
    return {"encontrado": False, "trecho": "", "motivo": "Consulta não localizada.", "parcial": False}


def localizar_trecho_em_documento(
    sections: list[dict],
    consulta: str,
    janela: int = 30,
) -> dict:
    """Search across document sections. Returns match with page/offset anchor.

    Each section dict has keys: title, page, start, text.
    """
    con_norm = normalizar(consulta)

    for sec in sections:
        sec_text = sec.get("text", "")
        sec_norm = normalizar(sec_text)
        if con_norm in sec_norm:
            pos = sec_norm.index(con_norm)
            end = pos + len(con_norm)
            start_offset = sec.get("start", 0) + pos
            end_offset = sec.get("start", 0) + end
            words = sec_text.split()
            w_idx = 0
            acc = 0
            for i, w in enumerate(words):
                if acc >= pos:
                    w_idx = i
                    break
                acc += len(w) + 1
            trecho = " ".join(words[max(0, w_idx - 3): w_idx + janela])
            return {
                "encontrado": True,
                "trecho": trecho,
                "pagina": sec.get("page", 0),
                "start_offset": start_offset,
                "end_offset": end_offset,
                "secao": sec.get("title", ""),
                "parcial": False,
            }

    for sec in sections:
        sec_text = sec.get("text", "")
        sec_norm = normalizar(sec_text)
        tokens = con_norm.split()
        if len(tokens) >= 4:
            metade = len(tokens) // 2
            for sub in [tokens[:metade + 2], tokens[metade - 1:]]:
                ss = " ".join(sub)
                if ss in sec_norm:
                    pos = sec_norm.index(ss)
                    start_offset = sec.get("start", 0) + pos
                    end_offset = start_offset + len(ss)
                    words = sec_text.split()
                    w_idx = max(0, min(pos // 6, len(words) - 1))
                    trecho = " ".join(words[max(0, w_idx - 3): w_idx + janela])
                    return {
                        "encontrado": True,
                        "trecho": trecho,
                        "pagina": sec.get("page", 0),
                        "start_offset": start_offset,
                        "end_offset": end_offset,
                        "secao": sec.get("title", ""),
                        "parcial": True,
                    }

    return {
        "encontrado": False,
        "trecho": "",
        "motivo": "Consulta não localizada no documento.",
        "parcial": False,
    }
