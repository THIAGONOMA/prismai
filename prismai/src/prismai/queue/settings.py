"""SAQ worker settings — importable as ``prismai.queue.settings.saq_settings``."""
from __future__ import annotations

from saq import Queue

from prismai.config import settings
from prismai.queue.tasks import (
    run_dual_screening_task,
    run_eligibility_task,
    run_extraction_task,
    run_fulltext_fetch_task,
    run_grade_task,
    run_living_update_task,
    run_report_task,
    run_rob_task,
    run_screening_task,
    run_synthesis_task,
)

queue = Queue.from_url(settings.saq_queue_url)

saq_settings = {
    "queue": queue,
    "functions": [
        run_screening_task, run_dual_screening_task, run_fulltext_fetch_task,
        run_eligibility_task, run_extraction_task, run_rob_task,
        run_synthesis_task, run_grade_task, run_report_task,
        run_living_update_task,
    ],
    "concurrency": settings.saq_concurrency,
}
