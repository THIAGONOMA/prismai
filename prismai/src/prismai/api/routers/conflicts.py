from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from prismai.api.deps import get_repo
from prismai.api.schemas import AgreementResponse, ConflictResponse, ResolveConflictRequest
from prismai.eval.agreement import cohens_kappa
from prismai.persistence.repository import ReviewRepository

router = APIRouter(prefix="/v1/reviews", tags=["conflicts"])


@router.get("/{review_id}/conflicts", response_model=list[ConflictResponse])
async def list_conflicts(
    review_id: str,
    status: str | None = None,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")
    conflicts = await repo.get_conflicts(review_id, status=status)
    return conflicts


@router.post("/{review_id}/conflicts/{registro_id}/resolve", response_model=ConflictResponse)
async def resolve_conflict(
    review_id: str,
    registro_id: str,
    body: ResolveConflictRequest,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")
    try:
        await repo.resolve_conflict(review_id, registro_id, body.decision, body.note)
    except KeyError:
        raise HTTPException(404, f"Conflict for registro '{registro_id}' not found")

    await repo.add_decision(review_id, {
        "registro_id": registro_id,
        "decision": body.decision,
        "confidence": "high",
        "reasons": [f"Human resolution: {body.note}" if body.note else "Human resolution"],
        "evidence": [],
        "degradado": False,
        "alertas": [],
    }, screener="human")

    conflicts = await repo.get_conflicts(review_id)
    for c in conflicts:
        if c["registro_id"] == registro_id:
            return c
    raise HTTPException(500, "Conflict resolved but not found after update")


@router.get("/{review_id}/agreement", response_model=AgreementResponse)
async def get_agreement(
    review_id: str,
    repo: ReviewRepository = Depends(get_repo),
):
    review = await repo.get_review(review_id)
    if not review:
        raise HTTPException(404, f"Review '{review_id}' not found")

    decisions = await repo.get_decisions(review_id)
    primary = {d["registro_id"]: d["decision"] for d in decisions if d.get("screener") == "primary"}
    secondary = {d["registro_id"]: d["decision"] for d in decisions if d.get("screener") == "secondary"}

    common_ids = sorted(set(primary) & set(secondary))
    if not common_ids:
        return AgreementResponse(kappa=0.0, n_total=0, n_agree=0, n_conflict=0)

    labels_a = [primary[rid] for rid in common_ids]
    labels_b = [secondary[rid] for rid in common_ids]
    kappa = cohens_kappa(labels_a, labels_b)
    n_agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)

    return AgreementResponse(
        kappa=round(kappa, 4),
        n_total=len(common_ids),
        n_agree=n_agree,
        n_conflict=len(common_ids) - n_agree,
    )
