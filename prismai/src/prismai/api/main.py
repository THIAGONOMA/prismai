from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prismai.api.routers import (
    auth,
    conflicts,
    documents,
    eligibility,
    extraction,
    file_import,
    grade,
    jobs,
    living,
    report,
    reviews,
    rob,
    screening,
    search,
    synthesis,
)

app = FastAPI(title="prismai", version="0.1.0", description="Copiloto PRISMA para screening de revisão sistemática")

from prismai.config import settings as _settings  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reviews.router)
app.include_router(screening.router)
app.include_router(search.router)
app.include_router(file_import.router)
app.include_router(jobs.router)
app.include_router(conflicts.router)
app.include_router(documents.router)
app.include_router(eligibility.router)
app.include_router(extraction.router)
app.include_router(rob.router)
app.include_router(synthesis.router)
app.include_router(grade.router)
app.include_router(report.router)
app.include_router(living.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
