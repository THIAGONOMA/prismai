"""PRISMA 2020 checklist — 27 items resolved against the dossie."""
from __future__ import annotations

from prismai.core.models import ChecklistItem, ChecklistResult, PrismaFlowCounts


def _has_protocol(d: dict) -> bool:
    return d.get("protocol") is not None


def _has_protocol_field(d: dict, *keys: str) -> bool:
    p = d.get("protocol")
    if not p:
        return False
    return all(bool(p.get(k)) for k in keys)


def _has_import_runs(d: dict) -> bool:
    return len(d.get("import_runs", [])) > 0


def _has_records(d: dict) -> bool:
    return len(d.get("records", [])) > 0


def _has_decisions(d: dict) -> bool:
    return len(d.get("decisions", [])) > 0


def _has_documents(d: dict) -> bool:
    return len(d.get("documents", [])) > 0


def _has_eligibility(d: dict) -> bool:
    return len(d.get("eligibility", [])) > 0


def _has_extractions(d: dict) -> bool:
    return len(d.get("extractions", [])) > 0


def _has_rob(d: dict) -> bool:
    return len(d.get("rob", [])) > 0


def _has_syntheses(d: dict) -> bool:
    return len(d.get("syntheses", [])) > 0


def _has_grade(d: dict) -> bool:
    return len(d.get("grade", [])) > 0


PRISMA2020_ITEMS: list[dict] = [
    {"numero": "1", "secao": "Título", "titulo": "Identificar o relato como revisão sistemática",
     "resolver": lambda d, f: _has_protocol(d)},
    {"numero": "2", "secao": "Resumo", "titulo": "Resumo estruturado",
     "resolver": lambda d, f: _has_protocol(d)},
    {"numero": "3", "secao": "Introdução", "titulo": "Descrever a justificativa da revisão",
     "resolver": lambda d, f: _has_protocol_field(d, "pergunta")},
    {"numero": "4", "secao": "Introdução", "titulo": "Objetivos explícitos com PICO",
     "resolver": lambda d, f: _has_protocol_field(d, "P", "I", "C", "O")},
    {"numero": "5", "secao": "Métodos", "titulo": "Critérios de elegibilidade",
     "resolver": lambda d, f: _has_protocol_field(d, "inclusao", "exclusao")},
    {"numero": "6", "secao": "Métodos", "titulo": "Fontes de informação",
     "resolver": lambda d, f: _has_import_runs(d)},
    {"numero": "7", "secao": "Métodos", "titulo": "Estratégia de busca",
     "resolver": lambda d, f: any(r.get("query") for r in d.get("import_runs", []))},
    {"numero": "8", "secao": "Métodos", "titulo": "Processo de seleção",
     "resolver": lambda d, f: _has_decisions(d)},
    {"numero": "9", "secao": "Métodos", "titulo": "Processo de coleta de dados",
     "resolver": lambda d, f: _has_extractions(d)},
    {"numero": "10a", "secao": "Métodos", "titulo": "Itens de dados — desfechos",
     "resolver": lambda d, f: _has_extractions(d)},
    {"numero": "10b", "secao": "Métodos", "titulo": "Itens de dados — outros",
     "resolver": lambda d, f: _has_extractions(d)},
    {"numero": "11", "secao": "Métodos", "titulo": "Avaliação do risco de viés nos estudos",
     "resolver": lambda d, f: _has_rob(d)},
    {"numero": "12", "secao": "Métodos", "titulo": "Medidas de efeito",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "13a", "secao": "Métodos", "titulo": "Métodos de síntese — elegibilidade",
     "resolver": lambda d, f: _has_eligibility(d)},
    {"numero": "13b", "secao": "Métodos", "titulo": "Métodos de síntese — preparação de dados",
     "resolver": lambda d, f: _has_extractions(d)},
    {"numero": "13c", "secao": "Métodos", "titulo": "Métodos de síntese — tabulação",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "13d", "secao": "Métodos", "titulo": "Métodos de síntese — modelo estatístico",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "13e", "secao": "Métodos", "titulo": "Métodos de síntese — heterogeneidade",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "13f", "secao": "Métodos", "titulo": "Métodos de síntese — análise de sensibilidade",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "14", "secao": "Métodos", "titulo": "Avaliação do viés de publicação",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "15", "secao": "Métodos", "titulo": "Avaliação da certeza da evidência",
     "resolver": lambda d, f: _has_grade(d)},
    {"numero": "16a", "secao": "Resultados", "titulo": "Seleção de estudos — fluxograma",
     "resolver": lambda d, f: f.registros_triados > 0},
    {"numero": "16b", "secao": "Resultados", "titulo": "Seleção de estudos — exclusões",
     "resolver": lambda d, f: _has_eligibility(d)},
    {"numero": "17", "secao": "Resultados", "titulo": "Características dos estudos",
     "resolver": lambda d, f: _has_extractions(d)},
    {"numero": "18", "secao": "Resultados", "titulo": "Risco de viés nos estudos",
     "resolver": lambda d, f: _has_rob(d)},
    {"numero": "19", "secao": "Resultados", "titulo": "Resultados dos estudos individuais",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "20a", "secao": "Resultados", "titulo": "Resultados das sínteses — sumário",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "20b", "secao": "Resultados", "titulo": "Resultados das sínteses — forest plot",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "20c", "secao": "Resultados", "titulo": "Resultados das sínteses — heterogeneidade",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "20d", "secao": "Resultados", "titulo": "Resultados das sínteses — sensibilidade",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "21", "secao": "Resultados", "titulo": "Viés de publicação",
     "resolver": lambda d, f: _has_syntheses(d)},
    {"numero": "22", "secao": "Resultados", "titulo": "Certeza da evidência",
     "resolver": lambda d, f: _has_grade(d)},
    {"numero": "23a", "secao": "Discussão", "titulo": "Discussão — interpretação geral",
     "resolver": lambda d, f: False},
    {"numero": "23b", "secao": "Discussão", "titulo": "Discussão — limitações da evidência",
     "resolver": lambda d, f: False},
    {"numero": "23c", "secao": "Discussão", "titulo": "Discussão — limitações do processo",
     "resolver": lambda d, f: False},
    {"numero": "23d", "secao": "Discussão", "titulo": "Discussão — implicações",
     "resolver": lambda d, f: False},
    {"numero": "24a", "secao": "Outras informações", "titulo": "Registro e protocolo — registro",
     "resolver": lambda d, f: _has_protocol(d)},
    {"numero": "24b", "secao": "Outras informações", "titulo": "Registro e protocolo — desvios",
     "resolver": lambda d, f: False},
    {"numero": "24c", "secao": "Outras informações", "titulo": "Registro e protocolo — emendas",
     "resolver": lambda d, f: False},
    {"numero": "24d", "secao": "Outras informações", "titulo": "Registro e protocolo — acesso",
     "resolver": lambda d, f: _has_protocol(d)},
    {"numero": "25", "secao": "Outras informações", "titulo": "Apoio/financiamento",
     "resolver": lambda d, f: False},
    {"numero": "26", "secao": "Outras informações", "titulo": "Conflitos de interesse",
     "resolver": lambda d, f: False},
    {"numero": "27", "secao": "Outras informações", "titulo": "Disponibilidade de dados",
     "resolver": lambda d, f: _has_records(d)},
]


def preencher_checklist(dossie: dict, flow: PrismaFlowCounts) -> ChecklistResult:
    itens: list[ChecklistItem] = []
    n_atendidos = 0
    for item_def in PRISMA2020_ITEMS:
        resolver = item_def["resolver"]
        atendido = bool(resolver(dossie, flow))
        if atendido:
            n_atendidos += 1
        itens.append(ChecklistItem(
            numero=item_def["numero"],
            secao=item_def["secao"],
            titulo=item_def["titulo"],
            atendido=atendido,
        ))
    return ChecklistResult(itens=itens, n_atendidos=n_atendidos)
