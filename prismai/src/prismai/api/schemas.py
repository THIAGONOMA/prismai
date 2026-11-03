from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateReviewRequest(BaseModel):
    id: str


class ProtocolRequest(BaseModel):
    pergunta: str
    P: str
    I: str
    C: str
    O: str
    desenho: str
    inclusao: list[str]
    exclusao: list[str]


class RecordInput(BaseModel):
    id: str
    titulo: str
    abstract: str
    doi: str | None = None
    authors: list[str] = []
    year: int | None = None
    source: str = "manual"


class ImportRecordsRequest(BaseModel):
    records: list[RecordInput]


class ImportResponse(BaseModel):
    imported: int
    duplicates: int


class SearchRequest(BaseModel):
    source: str = "openalex"
    query: str
    max_results: int = 200


class SearchResponse(BaseModel):
    imported: int
    duplicates: int
    total_found: int


class FileImportResponse(BaseModel):
    imported: int
    duplicates: int
    format: str


class RunScreeningRequest(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0
    mode: str = "single"
    model_b: str | None = None
    model_auditor: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    total: int = 0


class DecisionResponse(BaseModel):
    registro_id: str
    decision: str
    confidence: str
    reasons: list[str]
    evidence: list[str]
    degradado: bool = False
    alertas: list[str] = []


class ConflictResponse(BaseModel):
    registro_id: str
    decision_a: str
    decision_b: str
    screener_a: str
    screener_b: str
    disagreement_score: float
    status: str
    resolved_decision: str | None = None
    resolved_note: str | None = None
    resolved_at: str | None = None


class ResolveConflictRequest(BaseModel):
    decision: str
    note: str = ""


class AgreementResponse(BaseModel):
    kappa: float
    n_total: int
    n_agree: int
    n_conflict: int


class DocumentResponse(BaseModel):
    record_id: str
    status: str
    fetch_source: str | None = None
    n_pages: int = 0
    ocr_confidence: float | None = None
    extraction_method: str | None = None
    error: str | None = None


class FulltextFetchResponse(BaseModel):
    job_id: str
    status: str


class EligibilityDecisionResponse(BaseModel):
    document_id: str | None = None
    decision: str
    exclusion_reason: str | None = None
    confidence: str
    reasons: list[str] = []
    degradado: bool = False
    alertas: list[str] = []


class RunEligibilityRequest(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0


class RunExtractionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0


class ExtractionCellResponse(BaseModel):
    field: str
    block: str
    value: Any = None
    value_type: str = "text"
    page: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    evidence_text: str | None = None
    confidence: str = "low"
    needs_human_confirmation: bool = False
    flags: list[str] = []


class ExtractionResponse(BaseModel):
    record_id: str
    schema_version: str = ""
    status: str = "pending"
    cells: list[ExtractionCellResponse] = []
    consistency_flags: list[str] = []
    degradado: bool = False
    alertas: list[str] = []


class ExtractionSchemaRequest(BaseModel):
    schema_data: dict


class RobAssessmentResponse(BaseModel):
    record_id: str
    instrument: str = "rob2"
    overall_judgment: str = ""
    domain_results: list[dict] = []
    degradado: bool = False
    alertas: list[str] = []


class RunRobRequest(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0


class SynthesisConfigRequest(BaseModel):
    config: dict


class RunSynthesisRequest(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0


class StudyEffectResponse(BaseModel):
    record_id: str
    incluido: bool = True
    yi: float | None = None
    vi: float | None = None
    se: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    weight_fixed: float | None = None
    weight_random: float | None = None
    n_total: int | None = None
    rob: str | None = None


class SynthesisResponse(BaseModel):
    outcome_key: str
    measure: str = ""
    model: str = "random"
    k_studies: int = 0
    pooled_effect: float | None = None
    se: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    tau2: float | None = None
    i2: float | None = None
    study_effects: list[StudyEffectResponse] = []
    status: str = "draft"
    degradado: bool = False
    alertas: list[str] = []


class RunGradeRequest(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0


class GradeDomainResponse(BaseModel):
    domain: str
    rating: int = 0
    justificativa: str = ""
    automatico: bool = True


class GradeAssessmentResponse(BaseModel):
    outcome_key: str
    starting_certainty: str = "high"
    domains: list[GradeDomainResponse] = []
    final_certainty: str = "high"
    k_studies: int = 0
    status: str = "draft"
    degradado: bool = False
    alertas: list[str] = []


class SofEntry(BaseModel):
    outcome_key: str
    measure: str = ""
    k_studies: int = 0
    n_participants: int | None = None
    pooled_effect: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    certainty: str = ""
    rob_downgrade: int = 0
    inconsistency_downgrade: int = 0
    indirectness_downgrade: int = 0
    imprecision_downgrade: int = 0
    pub_bias_downgrade: int = 0


class SofResponse(BaseModel):
    entries: list[SofEntry] = []


class FlowDiscrepancyResponse(BaseModel):
    invariante: str
    esperado: int
    encontrado: int
    detalhe: str = ""


class FlowCountsResponse(BaseModel):
    identificados_por_fonte: dict[str, int] = {}
    identificados_total: int = 0
    duplicatas_removidas: int = 0
    registros_triados: int = 0
    registros_excluidos: int = 0
    fulltext_buscados: int = 0
    fulltext_nao_recuperados: int = 0
    fulltext_avaliados: int = 0
    fulltext_excluidos_por_motivo: dict[str, int] = {}
    estudos_incluidos: int = 0
    triagem_pendente: int = 0
    conflitos_nao_resolvidos: int = 0
    discrepancias: list[FlowDiscrepancyResponse] = []


class ChecklistItemResponse(BaseModel):
    numero: str
    secao: str
    titulo: str
    atendido: bool = False
    ponteiro: str = ""
    nota: str = ""


class ChecklistResponse(BaseModel):
    version: str = "prisma-2020"
    itens: list[ChecklistItemResponse] = []
    n_atendidos: int = 0


class ReportSectionResponse(BaseModel):
    key: str
    titulo: str
    corpo: str = ""
    numeros_citados: list[float] = []
    flags: list[str] = []


class ReportResponse(BaseModel):
    kind: str = "prisma"
    status: str = "draft"
    flow_counts: dict | None = None
    discrepancies: list[dict] = []
    checklist: dict | None = None
    sections: list[dict] = []
    artifacts: dict | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    degradado: bool = False
    alertas: list[str] = []


class RunReportRequest(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0


class EnableLivingRequest(BaseModel):
    cron: str = "0 3 * * 1"


class RunLivingRequest(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0


class ImpactDetailResponse(BaseModel):
    outcome_key: str
    tipo: str
    descricao: str
    antes: float | None = None
    depois: float | None = None


class LivingUpdateResponse(BaseModel):
    trigger: str = "manual"
    search_sources: list[str] = []
    new_found: int = 0
    new_imported: int = 0
    new_duplicates: int = 0
    screening_status: str = "pending"
    impact_status: str = "pending"
    impact_result: dict | None = None
    notified: bool = False
    created_at: str | None = None


class LivingStatusResponse(BaseModel):
    enabled: bool = False
    cron: str | None = None
    total_updates: int = 0
    last_update: dict | None = None
    pending_notifications: int = 0
