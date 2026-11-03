from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    users: Mapped[list[User]] = relationship(back_populates="org", cascade="all, delete-orphan")
    reviews: Mapped[list[Review]] = relationship(back_populates="org", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    org: Mapped[Org] = relationship(back_populates="users")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_review_org_slug"),)

    living_enabled: Mapped[bool] = mapped_column(default=False)
    living_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    living_last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    org: Mapped[Org] = relationship(back_populates="reviews")
    protocol: Mapped[Protocol | None] = relationship(
        back_populates="review", uselist=False, cascade="all, delete-orphan",
    )
    records: Mapped[list[Record]] = relationship(back_populates="review", cascade="all, delete-orphan")
    decisions: Mapped[list[Decision]] = relationship(back_populates="review", cascade="all, delete-orphan")
    conflicts: Mapped[list[Conflict]] = relationship(back_populates="review", cascade="all, delete-orphan")
    documents: Mapped[list[Document]] = relationship(back_populates="review", cascade="all, delete-orphan")
    eligibility_decisions: Mapped[list[EligibilityDecision]] = relationship(
        back_populates="review", cascade="all, delete-orphan",
    )
    traces: Mapped[list[Trace]] = relationship(back_populates="review", cascade="all, delete-orphan")
    jobs: Mapped[list[Job]] = relationship(back_populates="review", cascade="all, delete-orphan")
    extractions: Mapped[list[Extraction]] = relationship(back_populates="review", cascade="all, delete-orphan")
    rob_assessments: Mapped[list[RobAssessment]] = relationship(
        back_populates="review", cascade="all, delete-orphan",
    )
    syntheses: Mapped[list[Synthesis]] = relationship(back_populates="review", cascade="all, delete-orphan")
    grade_assessments: Mapped[list[GradeAssessment]] = relationship(
        back_populates="review", cascade="all, delete-orphan",
    )
    import_runs: Mapped[list[ImportRun]] = relationship(back_populates="review", cascade="all, delete-orphan")
    reports: Mapped[list[Report]] = relationship(back_populates="review", cascade="all, delete-orphan")
    living_updates: Mapped[list[LivingUpdate]] = relationship(back_populates="review", cascade="all, delete-orphan")


class Protocol(Base):
    __tablename__ = "protocols"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id"), unique=True, nullable=False,
    )
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    extraction_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    synthesis_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    review: Mapped[Review] = relationship(back_populates="protocol")


class Record(Base):
    __tablename__ = "records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    titulo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    abstract: Mapped[str] = mapped_column(Text, nullable=False, default="")
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    authors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    title_norm: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_records_review_doi", "review_id", "doi", unique=True, postgresql_where="doi IS NOT NULL"),
    )

    review: Mapped[Review] = relationship(back_populates="records")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    registro_id: Mapped[str] = mapped_column(String(255), nullable=False)
    screener: Mapped[str] = mapped_column(String(50), nullable=False, default="primary")
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    degradado: Mapped[bool] = mapped_column(default=False)
    alertas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("review_id", "registro_id", "screener", name="uq_decision_review_registro_screener"),
    )

    review: Mapped[Review] = relationship(back_populates="decisions")


class Conflict(Base):
    __tablename__ = "conflicts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    registro_id: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_a: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_b: Mapped[str] = mapped_column(String(50), nullable=False)
    screener_a: Mapped[str] = mapped_column(String(50), nullable=False)
    screener_b: Mapped[str] = mapped_column(String(50), nullable=False)
    disagreement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    resolved_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolved_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (UniqueConstraint("review_id", "registro_id", name="uq_conflict_review_registro"),)

    review: Mapped[Review] = relationship(back_populates="conflicts")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("records.id"), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    n_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    fetch_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (UniqueConstraint("review_id", "record_id", name="uq_document_review_record"),)

    review: Mapped[Review] = relationship(back_populates="documents")
    evidence_spans: Mapped[list[EvidenceSpan]] = relationship(back_populates="document", cascade="all, delete-orphan")


class EligibilityDecision(Base):
    __tablename__ = "eligibility_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    degradado: Mapped[bool] = mapped_column(default=False)
    alertas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (UniqueConstraint("review_id", "document_id", name="uq_eligibility_review_document"),)

    review: Mapped[Review] = relationship(back_populates="eligibility_decisions")


class EvidenceSpan(Base):
    __tablename__ = "evidence_spans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    criterion: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped[Document] = relationship(back_populates="evidence_spans")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False, default="cochrane-default-v2")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    degradado: Mapped[bool] = mapped_column(default=False)
    alertas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (UniqueConstraint("review_id", "document_id", name="uq_extraction_review_document"),)

    review: Mapped[Review] = relationship(back_populates="extractions")
    cells: Mapped[list[ExtractionCell]] = relationship(back_populates="extraction", cascade="all, delete-orphan")


class ExtractionCell(Base):
    __tablename__ = "extraction_cells"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extractions.id"), nullable=False,
    )
    field: Mapped[str] = mapped_column(String(255), nullable=False)
    block: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False, default="low")
    needs_human_confirmation: Mapped[bool] = mapped_column(default=False)
    flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    extraction: Mapped[Extraction] = relationship(back_populates="cells")


class RobAssessment(Base):
    __tablename__ = "rob_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    instrument: Mapped[str] = mapped_column(String(50), nullable=False, default="rob2")
    overall_judgment: Mapped[str] = mapped_column(String(50), nullable=False)
    domain_results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    degradado: Mapped[bool] = mapped_column(default=False)
    alertas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("review_id", "document_id", "instrument", name="uq_rob_review_document_instrument"),
    )

    review: Mapped[Review] = relationship(back_populates="rob_assessments")


class Synthesis(Base):
    __tablename__ = "syntheses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    outcome_key: Mapped[str] = mapped_column(String(255), nullable=False)
    measure: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False, default="random")
    k_studies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pooled_effect: Mapped[float | None] = mapped_column(Float, nullable=True)
    se: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    z: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    tau2: Mapped[float | None] = mapped_column(Float, nullable=True)
    q: Mapped[float | None] = mapped_column(Float, nullable=True)
    q_p: Mapped[float | None] = mapped_column(Float, nullable=True)
    i2: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    egger_intercept: Mapped[float | None] = mapped_column(Float, nullable=True)
    egger_p: Mapped[float | None] = mapped_column(Float, nullable=True)
    study_effects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    unmapped: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    degradado: Mapped[bool] = mapped_column(default=False)
    alertas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (UniqueConstraint("review_id", "outcome_key", name="uq_synthesis_review_outcome"),)

    review: Mapped[Review] = relationship(back_populates="syntheses")


class GradeAssessment(Base):
    __tablename__ = "grade_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    outcome_key: Mapped[str] = mapped_column(String(255), nullable=False)
    starting_certainty: Mapped[str] = mapped_column(String(50), nullable=False, default="high")
    domain_results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    final_certainty: Mapped[str] = mapped_column(String(50), nullable=False)
    k_studies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    degradado: Mapped[bool] = mapped_column(default=False)
    alertas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (UniqueConstraint("review_id", "outcome_key", name="uq_grade_review_outcome"),)

    review: Mapped[Review] = relationship(back_populates="grade_assessments")


class ImportRun(Base):
    __tablename__ = "import_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    review: Mapped[Review] = relationship(back_populates="import_runs")


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="prisma")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    flow_counts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    discrepancies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    checklist: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    artifacts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    degradado: Mapped[bool] = mapped_column(default=False)
    alertas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    __table_args__ = (UniqueConstraint("review_id", "kind", name="uq_report_review_kind"),)
    review: Mapped[Review] = relationship(back_populates="reports")


class LivingUpdate(Base):
    __tablename__ = "living_updates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    search_sources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    new_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    screening_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    impact_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    impact_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notified: Mapped[bool] = mapped_column(default=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    review: Mapped[Review] = relationship(back_populates="living_updates")


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    review: Mapped[Review] = relationship(back_populates="traces")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    review: Mapped[Review] = relationship(back_populates="jobs")
