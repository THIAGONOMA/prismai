"""Single aggregation point for all review data needed by the report."""
from __future__ import annotations

from prismai.persistence.repository import ReviewRepository


async def montar_dossie(repo: ReviewRepository, review_id: str) -> dict:
    """Collect all data for the report. Every report component uses this dict, never the repo directly."""
    protocol = await repo.get_protocol(review_id)
    import_runs = await repo.get_import_runs(review_id)
    records = await repo.get_records(review_id)
    decisions = await repo.get_decisions(review_id)
    conflicts = await repo.get_conflicts(review_id)
    documents = await repo.get_documents(review_id)
    eligibility = await repo.get_eligibility_decisions(review_id)
    extractions = await repo.get_extractions(review_id)
    rob = await repo.get_rob_assessments(review_id)
    syntheses = await repo.get_syntheses(review_id)
    grade = await repo.get_grade_assessments(review_id)
    return {
        "protocol": protocol,
        "import_runs": import_runs,
        "records": records,
        "decisions": decisions,
        "conflicts": conflicts,
        "documents": documents,
        "eligibility": eligibility,
        "extractions": extractions,
        "rob": rob,
        "syntheses": syntheses,
        "grade": grade,
    }
