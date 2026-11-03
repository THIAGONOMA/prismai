"""Build reproducibility package as ZIP."""
from __future__ import annotations

import json
import zipfile

from prismai.core.models import PrismaFlowCounts
from prismai.report.diagram import render_prisma_svg
from prismai.report.render import render_html, render_markdown


def build_reproducibility_package(
    dossie: dict, report: dict, flow: PrismaFlowCounts, checklist: dict, output_path: str,
) -> str:
    """Create a ZIP file with all data for reproducibility."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if dossie.get("protocol"):
            zf.writestr("protocol.json", json.dumps(dossie["protocol"], ensure_ascii=False, indent=2))
        zf.writestr("import_runs.json", json.dumps(dossie.get("import_runs", []), ensure_ascii=False, indent=2))
        zf.writestr("records.json", json.dumps(dossie.get("records", []), ensure_ascii=False, indent=2))
        zf.writestr("decisions.json", json.dumps(dossie.get("decisions", []), ensure_ascii=False, indent=2))
        zf.writestr("eligibility.json", json.dumps(dossie.get("eligibility", []), ensure_ascii=False, indent=2))
        zf.writestr("extractions.json", json.dumps(dossie.get("extractions", []), ensure_ascii=False, indent=2))
        zf.writestr("rob.json", json.dumps(dossie.get("rob", []), ensure_ascii=False, indent=2))
        zf.writestr("syntheses.json", json.dumps(dossie.get("syntheses", []), ensure_ascii=False, indent=2))
        zf.writestr("grade.json", json.dumps(dossie.get("grade", []), ensure_ascii=False, indent=2))
        zf.writestr("checklist.json", json.dumps(checklist, ensure_ascii=False, indent=2))

        svg = render_prisma_svg(flow)
        zf.writestr("prisma_flow.svg", svg)

        md = render_markdown(report, flow, checklist)
        zf.writestr("report.md", md)

        html = render_html(report, flow, checklist)
        zf.writestr("report.html", html)

    return output_path
