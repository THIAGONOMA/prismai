from __future__ import annotations

import logging
import tempfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response

from prismai.api.deps import get_repo
from prismai.api.schemas import (
    ChecklistResponse,
    FlowCountsResponse,
    JobResponse,
    ReportResponse,
    RunReportRequest,
)
from prismai.core.models import PrismaFlowCounts
from prismai.persistence.repository import ReviewRepository
from prismai.report.dossier import montar_dossie
from prismai.report.flow import contar_fluxo

router = APIRouter(prefix="/v1/reviews", tags=["report"])
logger = logging.getLogger(__name__)


async def _get_flow(repo: ReviewRepository, review_id: str) -> PrismaFlowCounts:
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")
    dossie = await montar_dossie(repo, review_id)
    return contar_fluxo(dossie)


@router.get("/{review_id}/prisma-flow", response_model=FlowCountsResponse)
async def get_prisma_flow(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    flow = await _get_flow(repo, review_id)
    return FlowCountsResponse(**flow.model_dump())


@router.get("/{review_id}/prisma-flow.svg")
async def get_prisma_flow_svg(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    from prismai.report.diagram import render_prisma_svg

    flow = await _get_flow(repo, review_id)
    svg = render_prisma_svg(flow)
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/{review_id}/prisma-flow.png")
async def get_prisma_flow_png(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    from prismai.report.diagram import render_prisma_png

    flow = await _get_flow(repo, review_id)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        render_prisma_png(flow, f.name)
        f.seek(0)
        data = open(f.name, "rb").read()
    return Response(content=data, media_type="image/png")


@router.get("/{review_id}/checklist", response_model=ChecklistResponse)
async def get_checklist(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    from prismai.report.checklist import preencher_checklist

    flow = await _get_flow(repo, review_id)
    dossie = await montar_dossie(repo, review_id)
    checklist = preencher_checklist(dossie, flow)
    return ChecklistResponse(**checklist.model_dump())


@router.post("/{review_id}/report/run", response_model=JobResponse, status_code=202)
async def run_report(
    review_id: str,
    body: RunReportRequest | None = None,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if review is None:
        raise HTTPException(404, f"Review '{review_id}' not found")

    from prismai.api.jobs import create_job

    job = create_job(review_id, total=1)
    model = body.model if body else "gpt-4o-mini"
    temperature = body.temperature if body else 0

    try:
        from prismai.queue.settings import queue
        from prismai.queue.tasks import run_report_task

        await queue.enqueue(
            run_report_task,
            job_id=job.id, review_id=review_id, org_id="",
            model=model, temperature=temperature,
        )
    except Exception:
        import asyncio

        from prismai.queue.tasks import run_report_task

        asyncio.create_task(run_report_task(
            {}, job_id=job.id, review_id=review_id, org_id="",
            model=model, temperature=temperature,
        ))

    return JobResponse(job_id=job.id, status="running", total=1)


@router.get("/{review_id}/report", response_model=ReportResponse)
async def get_report(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    report = await repo.get_report(review_id, kind="prisma")
    if report is None:
        raise HTTPException(404, "Report not found")
    return ReportResponse(**report)


@router.post("/{review_id}/report/approve")
async def approve_report(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    try:
        await repo.approve_report(review_id, "prisma", "api_user")
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return {"ok": True}


@router.get("/{review_id}/report.md")
async def get_report_md(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    from prismai.report.render import render_markdown

    report = await repo.get_report(review_id, kind="prisma")
    if report is None:
        raise HTTPException(404, "Report not found")
    flow = PrismaFlowCounts(**(report.get("flow_counts") or {}))
    checklist = report.get("checklist", {})
    md = render_markdown(report, flow, checklist)
    return Response(content=md, media_type="text/markdown")


@router.get("/{review_id}/report.html")
async def get_report_html(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    from prismai.report.render import render_html

    report = await repo.get_report(review_id, kind="prisma")
    if report is None:
        raise HTTPException(404, "Report not found")
    flow = PrismaFlowCounts(**(report.get("flow_counts") or {}))
    checklist = report.get("checklist", {})
    html = render_html(report, flow, checklist)
    return HTMLResponse(content=html)


@router.get("/{review_id}/report.docx")
async def get_report_docx(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    from prismai.report.render import render_docx

    report = await repo.get_report(review_id, kind="prisma")
    if report is None:
        raise HTTPException(404, "Report not found")
    flow = PrismaFlowCounts(**(report.get("flow_counts") or {}))
    checklist = report.get("checklist", {})
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        render_docx(report, flow, checklist, f.name)
        data = open(f.name, "rb").read()
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": "attachment; filename=report.docx"})


@router.get("/{review_id}/export")
async def export_package(review_id: str, repo: ReviewRepository = Depends(get_repo)):
    from prismai.report.export import build_reproducibility_package

    report = await repo.get_report(review_id, kind="prisma")
    if report is None:
        raise HTTPException(404, "Report not found — run report first")
    dossie = await montar_dossie(repo, review_id)
    flow = PrismaFlowCounts(**(report.get("flow_counts") or {}))
    checklist = report.get("checklist", {})
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        build_reproducibility_package(dossie, report, flow, checklist, f.name)
        data = open(f.name, "rb").read()
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition": f"attachment; filename={review_id}_prisma_package.zip"})
