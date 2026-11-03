"""PRISMA 2020 flow diagram — SVG and PNG renderers."""
from __future__ import annotations

from prismai.core.models import PrismaFlowCounts


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_prisma_svg(flow: PrismaFlowCounts) -> str:
    """Generate PRISMA 2020 flow diagram as SVG string — hand-crafted, zero dependencies."""
    w, h = 800, 700
    box_w, box_h = 220, 50
    font = 'font-family="Arial, sans-serif" font-size="12"'
    small = 'font-family="Arial, sans-serif" font-size="10"'

    sources_text = ", ".join(f"{s}: {n}" for s, n in sorted(flow.identificados_por_fonte.items()))
    excl_reasons = ", ".join(f"{r} (n={n})" for r, n in sorted(flow.fulltext_excluidos_por_motivo.items()))

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">')
    lines.append('<style>rect{fill:#f0f4f8;stroke:#334155;stroke-width:1.5;rx:6}text{fill:#1e293b}'
                 'line,polyline{stroke:#64748b;stroke-width:1.5;fill:none;marker-end:url(#arrow)}</style>')
    lines.append('<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
                 'markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/>'
                 '</marker></defs>')

    def box(x: int, y: int, label: str, sub: str = "") -> None:
        lines.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}"/>')
        lines.append(f'<text x="{x + box_w // 2}" y="{y + 20}" text-anchor="middle" {font}>'
                     f'{_escape(label)}</text>')
        if sub:
            lines.append(f'<text x="{x + box_w // 2}" y="{y + 36}" text-anchor="middle" {small}>'
                         f'{_escape(sub)}</text>')

    cx = w // 2 - box_w // 2
    rx = w - box_w - 40

    box(cx, 20, "Identificação", f"n = {flow.identificados_total}")
    if sources_text:
        lines.append(f'<text x="{cx + box_w // 2}" y="85" text-anchor="middle" {small}>'
                     f'{_escape(sources_text)}</text>')

    box(rx, 20, "Duplicatas removidas", f"n = {flow.duplicatas_removidas}")
    lines.append(f'<line x1="{cx + box_w}" y1="45" x2="{rx}" y2="45"/>')

    box(cx, 120, "Registros triados", f"n = {flow.registros_triados}")
    lines.append(f'<line x1="{cx + box_w // 2}" y1="70" x2="{cx + box_w // 2}" y2="120"/>')

    box(rx, 120, "Excluídos na triagem", f"n = {flow.registros_excluidos}")
    lines.append(f'<line x1="{cx + box_w}" y1="145" x2="{rx}" y2="145"/>')

    box(cx, 230, "Full-text buscados", f"n = {flow.fulltext_buscados}")
    lines.append(f'<line x1="{cx + box_w // 2}" y1="170" x2="{cx + box_w // 2}" y2="230"/>')

    box(rx, 230, "Não recuperados", f"n = {flow.fulltext_nao_recuperados}")
    lines.append(f'<line x1="{cx + box_w}" y1="255" x2="{rx}" y2="255"/>')

    box(cx, 340, "Full-text avaliados", f"n = {flow.fulltext_avaliados}")
    lines.append(f'<line x1="{cx + box_w // 2}" y1="280" x2="{cx + box_w // 2}" y2="340"/>')

    excl_label = f"n = {sum(flow.fulltext_excluidos_por_motivo.values())}"
    box(rx, 340, "Excluídos no full-text", excl_label)
    lines.append(f'<line x1="{cx + box_w}" y1="365" x2="{rx}" y2="365"/>')
    if excl_reasons:
        lines.append(f'<text x="{rx + box_w // 2}" y="405" text-anchor="middle" {small}>'
                     f'{_escape(excl_reasons[:80])}</text>')

    box(cx, 450, "Estudos incluídos", f"n = {flow.estudos_incluidos}")
    lines.append(f'<line x1="{cx + box_w // 2}" y1="390" x2="{cx + box_w // 2}" y2="450"/>')

    if flow.triagem_pendente > 0:
        lines.append(f'<text x="40" y="160" {small} fill="#b45309">'
                     f'Triagem pendente: {flow.triagem_pendente}</text>')
    if flow.conflitos_nao_resolvidos > 0:
        lines.append(f'<text x="40" y="180" {small} fill="#b45309">'
                     f'Conflitos pendentes: {flow.conflitos_nao_resolvidos}</text>')

    if flow.discrepancias:
        y_warn = 530
        lines.append(f'<rect x="20" y="{y_warn}" width="{w - 40}" height="40" '
                     'style="fill:#fef3c7;stroke:#f59e0b;stroke-width:2"/>')
        warn_text = f"ATENÇÃO: {len(flow.discrepancias)} invariante(s) violada(s)"
        lines.append(f'<text x="{w // 2}" y="{y_warn + 25}" text-anchor="middle" {font} fill="#92400e">'
                     f'{_escape(warn_text)}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def render_prisma_png(flow: PrismaFlowCounts, path: str) -> str:
    """Render PRISMA diagram as PNG. Requires matplotlib (optional dep)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
    except ImportError as e:
        raise ImportError("matplotlib is required for PNG rendering: pip install prismai[plots]") from e

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def draw_box(x: float, y: float, w: float, h: float, label: str) -> None:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", facecolor="#f0f4f8", edgecolor="#334155")
        ax.add_patch(box)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=8, wrap=True)

    draw_box(2, 8.5, 3, 0.8, f"Identificação\nn = {flow.identificados_total}")
    draw_box(6, 8.5, 2.5, 0.8, f"Duplicatas\nn = {flow.duplicatas_removidas}")
    draw_box(2, 7, 3, 0.8, f"Triados\nn = {flow.registros_triados}")
    draw_box(6, 7, 2.5, 0.8, f"Excluídos\nn = {flow.registros_excluidos}")
    draw_box(2, 5.5, 3, 0.8, f"Full-text buscados\nn = {flow.fulltext_buscados}")
    draw_box(6, 5.5, 2.5, 0.8, f"Não recuperados\nn = {flow.fulltext_nao_recuperados}")
    draw_box(2, 4, 3, 0.8, f"Full-text avaliados\nn = {flow.fulltext_avaliados}")
    n_excl = sum(flow.fulltext_excluidos_por_motivo.values())
    draw_box(6, 4, 2.5, 0.8, f"Excluídos\nn = {n_excl}")
    draw_box(2, 2.5, 3, 0.8, f"Incluídos\nn = {flow.estudos_incluidos}")

    for (x1, y1, x2, y2) in [
        (5, 8.9, 6, 8.9), (3.5, 8.5, 3.5, 7.8), (5, 7.4, 6, 7.4),
        (3.5, 7, 3.5, 6.3), (5, 5.9, 6, 5.9), (3.5, 5.5, 3.5, 4.8),
        (5, 4.4, 6, 4.4), (3.5, 4, 3.5, 3.3),
    ]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color="#64748b"))

    if flow.discrepancias:
        ax.text(5, 1.5, f"ATENÇÃO: {len(flow.discrepancias)} invariante(s) violada(s)",
                ha="center", fontsize=10, color="#92400e",
                bbox=dict(boxstyle="round", facecolor="#fef3c7", edgecolor="#f59e0b"))

    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
