from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ScreeningResult(BaseModel):
    decision: Literal["include", "exclude", "uncertain"] = Field(description="Decisão de triagem.")
    reasons: list[str] = Field(description="Motivos referenciando PICO.")
    evidence: list[str] = Field(description="Trechos literais do abstract.")
    confidence: Literal["high", "medium", "low"] = Field(description="Nível de confiança.")


class Protocolo(BaseModel):
    pergunta: str
    P: str
    I: str
    C: str
    O: str
    desenho: str
    inclusao: list[str]
    exclusao: list[str]

    def formatar(self) -> str:
        """Format protocol for LLM prompt (port of formatar_protocolo)."""
        return (
            f"PERGUNTA DE PESQUISA: {self.pergunta}\n"
            f"P (População): {self.P}\nI (Intervenção): {self.I}\n"
            f"C (Comparação): {self.C}\nO (Desfecho): {self.O}\n"
            f"Desenho aceito: {self.desenho}\n"
            f"Critérios de inclusão: {'; '.join(self.inclusao)}\n"
            f"Critérios de exclusão: {'; '.join(self.exclusao)}"
        )


class Registro(BaseModel):
    id: str
    titulo: str
    abstract: str
    doi: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    source: str = "manual"


class EvidenceSpanRef(BaseModel):
    page: int
    start: int
    end: int
    text: str


class CriterionResult(BaseModel):
    criterion: str
    met: bool
    evidence_spans: list[EvidenceSpanRef] = Field(default_factory=list)
    reasoning: str = ""


class EligibilityResult(BaseModel):
    decision: Literal["include", "exclude"] = Field(description="Decisão de elegibilidade.")
    exclusion_reason: str | None = None
    criteria_results: list[CriterionResult] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = Field(description="Nível de confiança.")


class ExtractionFieldSpec(BaseModel):
    name: str
    block: str
    tipo: Literal["text", "number", "integer", "boolean", "list"]
    descricao: str
    obrigatorio: bool = False
    unidade: str | None = None


class ExtractionSchema(BaseModel):
    version: str = "cochrane-default-v2"
    fields: list[ExtractionFieldSpec]


class ExtractedCell(BaseModel):
    field: str
    block: str
    value: Any = None
    value_type: str = "text"
    evidence: EvidenceSpanRef | None = None
    confidence: Literal["high", "medium", "low"] = "low"
    needs_human_confirmation: bool = False
    flags: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    schema_version: str
    cells: list[ExtractedCell] = Field(default_factory=list)
    consistency_flags: list[str] = Field(default_factory=list)


class SignallingAnswer(BaseModel):
    question_id: str
    answer: Literal["Y", "PY", "PN", "N", "NI"]
    reasoning: str = ""
    evidence: EvidenceSpanRef | None = None


class DomainJudgment(BaseModel):
    domain: str
    judgment: Literal["low", "some_concerns", "high"]
    answers: list[SignallingAnswer] = Field(default_factory=list)


class RobResult(BaseModel):
    instrument: Literal["rob2"] = "rob2"
    domains: list[DomainJudgment] = Field(default_factory=list)
    overall: Literal["low", "some_concerns", "high"]


class OutcomeSpec(BaseModel):
    key: str
    nome: str
    tipo: Literal["continuous", "binary"]
    measure: Literal["smd", "md", "rr", "or"]
    direcao: Literal["higher_better", "lower_better"] = "higher_better"
    unidade: str | None = None
    mid: float | None = None
    sinonimos: list[str] = Field(default_factory=list)


class SynthesisConfig(BaseModel):
    version: str = "v1"
    outcomes: list[OutcomeSpec]


class StudyEffect(BaseModel):
    record_id: str
    incluido: bool = True
    motivo_exclusao: str | None = None
    yi: float | None = None
    vi: float | None = None
    se: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    weight_fixed: float | None = None
    weight_random: float | None = None
    n_total: int | None = None
    rob: str | None = None
    evidence: list[EvidenceSpanRef] = Field(default_factory=list)


class SynthesisResult(BaseModel):
    outcome_key: str
    measure: str
    model: Literal["fixed", "random"] = "random"
    k_studies: int = 0
    pooled_effect: float | None = None
    se: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    tau2: float | None = None
    q: float | None = None
    i2: float | None = None
    prediction_low: float | None = None
    prediction_high: float | None = None
    egger_intercept: float | None = None
    egger_p: float | None = None
    study_effects: list[StudyEffect] = Field(default_factory=list)


class GradeDomain(BaseModel):
    domain: Literal["risk_of_bias", "inconsistency", "indirectness", "imprecision", "publication_bias"]
    rating: Literal[0, -1, -2]
    justificativa: str = ""
    automatico: bool = True
    evidence: list[EvidenceSpanRef] = Field(default_factory=list)


class GradeResult(BaseModel):
    outcome_key: str
    starting_certainty: Literal["high", "low"]
    domains: list[GradeDomain] = Field(default_factory=list)
    final_certainty: Literal["high", "moderate", "low", "very_low"]


class FlowDiscrepancy(BaseModel):
    invariante: str
    esperado: int
    encontrado: int
    detalhe: str = ""


class PrismaFlowCounts(BaseModel):
    identificados_por_fonte: dict[str, int] = Field(default_factory=dict)
    identificados_total: int = 0
    duplicatas_removidas: int = 0
    registros_triados: int = 0
    registros_excluidos: int = 0
    fulltext_buscados: int = 0
    fulltext_nao_recuperados: int = 0
    fulltext_avaliados: int = 0
    fulltext_excluidos_por_motivo: dict[str, int] = Field(default_factory=dict)
    estudos_incluidos: int = 0
    triagem_pendente: int = 0
    conflitos_nao_resolvidos: int = 0
    discrepancias: list[FlowDiscrepancy] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    numero: str
    secao: str
    titulo: str
    atendido: bool = False
    ponteiro: str = ""
    nota: str = ""


class ChecklistResult(BaseModel):
    version: str = "prisma-2020"
    itens: list[ChecklistItem] = Field(default_factory=list)
    n_atendidos: int = 0


class ReportSection(BaseModel):
    key: Literal["metodos", "resultados"]
    titulo: str
    corpo: str = ""
    numeros_citados: list[float] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class ReportResult(BaseModel):
    flow: PrismaFlowCounts
    checklist: ChecklistResult
    sections: list[ReportSection] = Field(default_factory=list)


class CasoTeste(BaseModel):
    id: str
    registro_id: str
    tipo: str
    verificacao: Literal["auto", "manual"]
    esperado: Literal["include", "exclude", "uncertain"] | None = None
    aceitos: list[str] | None = None
    criterio_violado: list[str] | None = None
    tem_desfecho_academico: bool | None = None
    nota: str | None = None
