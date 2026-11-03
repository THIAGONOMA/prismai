"""Integration test for export.py — ZIP contents."""
from __future__ import annotations

import tempfile
import zipfile

from prismai.core.models import PrismaFlowCounts
from prismai.report.export import build_reproducibility_package


class TestExport:
    def test_zip_contents(self):
        dossie = {
            "protocol": {"pergunta": "test?"},
            "import_runs": [{"source": "openalex", "total_found": 10}],
            "records": [{"id": "r1"}],
            "decisions": [{"registro_id": "r1", "decision": "include"}],
            "eligibility": [],
            "extractions": [],
            "rob": [],
            "syntheses": [],
            "grade": [],
        }
        report = {
            "sections": [{"key": "metodos", "titulo": "Métodos", "corpo": "text"}],
        }
        flow = PrismaFlowCounts(identificados_total=10, registros_triados=1)
        checklist = {"version": "prisma-2020", "itens": [], "n_atendidos": 0}

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            path = build_reproducibility_package(dossie, report, flow, checklist, f.name)

        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            assert "protocol.json" in names
            assert "records.json" in names
            assert "decisions.json" in names
            assert "checklist.json" in names
            assert "prisma_flow.svg" in names
            assert "report.md" in names
            assert "report.html" in names
            assert "import_runs.json" in names
