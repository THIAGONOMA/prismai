"""Report writer — generates Métodos and Resultados sections with numeric audit."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from prismai.core.envelope import Resposta
from prismai.core.models import (
    ChecklistResult,
    PrismaFlowCounts,
    ReportResult,
    ReportSection,
)
from prismai.report.checklist import preencher_checklist

_SKILLS_DIR = Path(__file__).resolve().parent.parent / "agents" / "skills"


def _load_skill(name: str) -> str:
    return (_SKILLS_DIR / name).read_text(encoding="utf-8")


def _extrair_numeros(text: str) -> list[float]:
    """Extract all numbers from text."""
    raw = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    return [float(x) for x in raw]


def _numeros_validos(dossie: dict, flow: PrismaFlowCounts) -> set[float]:
    """Build set of all valid numbers from the dossie and flow counts."""
    nums: set[float] = set()
    fc = flow.model_dump()
    for v in fc.values():
        if isinstance(v, (int, float)):
            nums.add(float(v))
        elif isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, (int, float)):
                    nums.add(float(vv))

    for syn in dossie.get("syntheses", []):
        for k, v in syn.items():
            if isinstance(v, (int, float)):
                nums.add(float(v))

    for g in dossie.get("grade", []):
        for k, v in g.items():
            if isinstance(v, (int, float)):
                nums.add(float(v))

    for run in dossie.get("import_runs", []):
        for k, v in run.items():
            if isinstance(v, (int, float)):
                nums.add(float(v))

    nums.add(float(len(dossie.get("records", []))))
    nums.add(float(len(dossie.get("eligibility", []))))
    nums.add(float(len(dossie.get("extractions", []))))
    nums.add(float(len(dossie.get("rob", []))))

    return nums


def _build_skeleton(key: str, dossie: dict, flow: PrismaFlowCounts, checklist: ChecklistResult) -> str:
    """Build deterministic skeleton with all numbers from the dossie."""
    if key == "metodos":
        lines = [
            f"Total de registros identificados: {flow.identificados_total}.",
            f"Fontes: {', '.join(f'{s} ({n})' for s, n in sorted(flow.identificados_por_fonte.items()))}.",
            f"Duplicatas removidas: {flow.duplicatas_removidas}.",
            f"Registros triados: {flow.registros_triados}.",
            f"Registros excluídos na triagem: {flow.registros_excluidos}.",
            f"Full-text buscados: {flow.fulltext_buscados}.",
            f"Full-text não recuperados: {flow.fulltext_nao_recuperados}.",
            f"Full-text avaliados para elegibilidade: {flow.fulltext_avaliados}.",
            f"Estudos incluídos na síntese: {flow.estudos_incluidos}.",
        ]
        proto = dossie.get("protocol")
        if proto:
            p = proto.get("pergunta", "")
            if p:
                lines.insert(0, f"Pergunta de pesquisa: {p}")
        return "\n".join(lines)
    else:
        lines = [
            f"Total de estudos incluídos: {flow.estudos_incluidos}.",
        ]
        for syn in dossie.get("syntheses", []):
            pe = syn.get("pooled_effect")
            ci_l = syn.get("ci_low")
            ci_h = syn.get("ci_high")
            i2 = syn.get("i2")
            k = syn.get("k_studies", 0)
            ok = syn.get("outcome_key", "")
            if pe is not None:
                lines.append(f"Desfecho {ok}: efeito agrupado = {pe:.2f} (IC 95%: {ci_l:.2f}–{ci_h:.2f}), "
                             f"k = {k}, I² = {i2:.1f}%." if i2 is not None else
                             f"Desfecho {ok}: efeito agrupado = {pe:.2f} (IC 95%: {ci_l:.2f}–{ci_h:.2f}), k = {k}.")
        for g in dossie.get("grade", []):
            lines.append(f"Certeza ({g.get('outcome_key', '')}): {g.get('final_certainty', '')}.")
        return "\n".join(lines)


def _redigir_secao(key: str, dossie: dict, flow: PrismaFlowCounts,
                   checklist: ChecklistResult, llm: Any) -> ReportSection:
    """Build section: deterministic skeleton + LLM prose."""
    titulo = "Métodos" if key == "metodos" else "Resultados"
    skeleton = _build_skeleton(key, dossie, flow, checklist)

    skill_file = "redigir_metodos.md" if key == "metodos" else "redigir_resultados.md"
    try:
        skill = _load_skill(skill_file)
    except FileNotFoundError:
        skill = ""

    prompt = (
        f"{skill}\n\n"
        f"ESQUELETO NUMÉRICO (use APENAS estes números, não invente nenhum):\n{skeleton}\n\n"
        f"Escreva a seção '{titulo}' em prosa acadêmica, conectando os números acima. "
        f"Não introduza nenhum número que não esteja no esqueleto."
    )

    response = llm.invoke(prompt)
    corpo = response.content if hasattr(response, "content") else str(response)

    numeros_citados = _extrair_numeros(corpo)
    return ReportSection(key=key, titulo=titulo, corpo=corpo, numeros_citados=numeros_citados)


def _auditor_numerico(section: ReportSection, valid_numbers: set[float]) -> ReportSection:
    """Check all numbers in the section against valid set. Flag and remove invented ones."""
    flags: list[str] = []
    corpo = section.corpo
    for num in section.numeros_citados:
        if num not in valid_numbers:
            flags.append(f"Número {num} não encontrado nos dados — removido")
            pattern = re.compile(r"\b" + re.escape(str(int(num) if num == int(num) else num)) + r"\b")
            corpo = pattern.sub("[REMOVIDO]", corpo, count=1)
    return ReportSection(
        key=section.key,
        titulo=section.titulo,
        corpo=corpo,
        numeros_citados=[n for n in section.numeros_citados if n in valid_numbers],
        flags=flags,
    )


def draft_report(dossie: dict, flow: PrismaFlowCounts, llm: Any) -> tuple[Resposta[ReportResult], dict]:
    """Generate the report with audited sections."""
    checklist = preencher_checklist(dossie, flow)
    valid_nums = _numeros_validos(dossie, flow)

    sections: list[ReportSection] = []
    alertas: list[str] = []
    metricas: dict[str, Any] = {"step": "report"}

    for key in ("metodos", "resultados"):
        section = _redigir_secao(key, dossie, flow, checklist, llm)
        audited = _auditor_numerico(section, valid_nums)
        sections.append(audited)
        alertas.extend(audited.flags)

    result = ReportResult(flow=flow, checklist=checklist, sections=sections)
    degradado = bool(alertas)

    envelope = Resposta[ReportResult](
        resultado=result,
        degradado=degradado,
        motivo_degradacao="Números inventados removidos pelo auditor" if degradado else None,
        alertas=alertas,
    )
    metricas["n_flags"] = len(alertas)
    metricas["n_checklist_atendidos"] = checklist.n_atendidos
    return envelope, metricas
