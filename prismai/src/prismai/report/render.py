"""Render report in Markdown, HTML and DOCX."""
from __future__ import annotations

from prismai.core.models import PrismaFlowCounts


def render_markdown(report: dict, flow: PrismaFlowCounts, checklist: dict) -> str:
    lines: list[str] = ["# Relatório PRISMA 2020\n"]

    lines.append("## Fluxo PRISMA\n")
    lines.append(f"- Identificados: {flow.identificados_total}")
    lines.append(f"- Duplicatas removidas: {flow.duplicatas_removidas}")
    lines.append(f"- Triados: {flow.registros_triados}")
    lines.append(f"- Excluídos na triagem: {flow.registros_excluidos}")
    lines.append(f"- Full-text buscados: {flow.fulltext_buscados}")
    lines.append(f"- Full-text avaliados: {flow.fulltext_avaliados}")
    lines.append(f"- Estudos incluídos: {flow.estudos_incluidos}")
    lines.append("")

    for section in report.get("sections", []):
        lines.append(f"## {section.get('titulo', '')}\n")
        lines.append(section.get("corpo", ""))
        lines.append("")

    lines.append("## Checklist PRISMA 2020\n")
    itens = checklist.get("itens", []) if isinstance(checklist, dict) else []
    for item in itens:
        status = "✓" if item.get("atendido") else "✗"
        lines.append(f"- [{status}] {item.get('numero', '')} — {item.get('titulo', '')}")
    lines.append("")
    n_at = checklist.get("n_atendidos", 0) if isinstance(checklist, dict) else 0
    lines.append(f"**Total atendidos: {n_at}/{len(itens)}**\n")

    if flow.discrepancias:
        lines.append("## Alertas\n")
        for d in flow.discrepancias:
            lines.append(f"- ⚠ {d.invariante}: esperado {d.esperado}, encontrado {d.encontrado}")
        lines.append("")

    return "\n".join(lines)


def render_html(report: dict, flow: PrismaFlowCounts, checklist: dict) -> str:
    md = render_markdown(report, flow, checklist)
    try:
        from jinja2 import Template
    except ImportError:
        return f"<html><body><pre>{md}</pre></body></html>"

    template = Template("""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Relatório PRISMA 2020</title>
<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;line-height:1.6;color:#1e293b}
h1,h2{color:#0f172a}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd5e1;padding:0.5rem}
.warn{background:#fef3c7;border:1px solid #f59e0b;padding:0.5rem;border-radius:4px}</style></head>
<body>{{ content }}</body></html>""")

    html_body = md.replace("\n", "<br>\n")
    return template.render(content=html_body)


def render_docx(report: dict, flow: PrismaFlowCounts, checklist: dict, path: str) -> str:
    try:
        from docx import Document
    except ImportError as e:
        raise ImportError("python-docx is required: pip install prismai[report]") from e

    doc = Document()
    doc.add_heading("Relatório PRISMA 2020", level=0)

    doc.add_heading("Fluxo PRISMA", level=1)
    doc.add_paragraph(f"Identificados: {flow.identificados_total}")
    doc.add_paragraph(f"Duplicatas removidas: {flow.duplicatas_removidas}")
    doc.add_paragraph(f"Triados: {flow.registros_triados}")
    doc.add_paragraph(f"Excluídos na triagem: {flow.registros_excluidos}")
    doc.add_paragraph(f"Estudos incluídos: {flow.estudos_incluidos}")

    for section in report.get("sections", []):
        doc.add_heading(section.get("titulo", ""), level=1)
        doc.add_paragraph(section.get("corpo", ""))

    doc.add_heading("Checklist PRISMA 2020", level=1)
    itens = checklist.get("itens", []) if isinstance(checklist, dict) else []
    for item in itens:
        status = "✓" if item.get("atendido") else "✗"
        doc.add_paragraph(f"[{status}] {item.get('numero', '')} — {item.get('titulo', '')}")

    doc.save(path)
    return path
