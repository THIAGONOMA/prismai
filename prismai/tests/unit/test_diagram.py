"""Unit tests for report/diagram.py — PRISMA SVG rendering."""
from __future__ import annotations

from prismai.core.models import FlowDiscrepancy, PrismaFlowCounts
from prismai.report.diagram import render_prisma_svg


def _sample_flow(**overrides):
    defaults = {
        "identificados_por_fonte": {"openalex": 100},
        "identificados_total": 100,
        "duplicatas_removidas": 10,
        "registros_triados": 90,
        "registros_excluidos": 60,
        "fulltext_buscados": 30,
        "fulltext_nao_recuperados": 2,
        "fulltext_avaliados": 28,
        "fulltext_excluidos_por_motivo": {"sem dados": 8},
        "estudos_incluidos": 20,
    }
    defaults.update(overrides)
    return PrismaFlowCounts(**defaults)


class TestDiagramSVG:
    def test_svg_wellformed(self):
        flow = _sample_flow()
        svg = render_prisma_svg(flow)
        assert svg.startswith("<svg")
        assert "</svg>" in svg

    def test_svg_contains_key_strings(self):
        flow = _sample_flow()
        svg = render_prisma_svg(flow)
        assert "Identificação" in svg
        assert "n = 100" in svg
        assert "Estudos incluídos" in svg
        assert "n = 20" in svg
        assert "Duplicatas removidas" in svg

    def test_svg_warning_banner_with_discrepancy(self):
        flow = _sample_flow(discrepancias=[
            FlowDiscrepancy(invariante="test", esperado=10, encontrado=5),
        ])
        svg = render_prisma_svg(flow)
        assert "ATENÇÃO" in svg
        assert "1 invariante" in svg

    def test_svg_no_warning_without_discrepancy(self):
        flow = _sample_flow()
        svg = render_prisma_svg(flow)
        assert "ATENÇÃO" not in svg
