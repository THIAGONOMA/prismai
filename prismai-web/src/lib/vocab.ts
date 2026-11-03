export const SCREENING_DECISION = {
  include: { label: "Incluído", color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200" },
  exclude: { label: "Excluído", color: "text-red-600", bg: "bg-red-50", border: "border-red-200" },
  uncertain: { label: "Incerto", color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-200" },
} as const;

export const CONFIDENCE = {
  high: { label: "Alta", color: "text-emerald-700", dot: "bg-emerald-500" },
  medium: { label: "Média", color: "text-amber-700", dot: "bg-amber-500" },
  low: { label: "Baixa", color: "text-red-700", dot: "bg-red-500" },
} as const;

export const ROB2_JUDGMENT = {
  low: { label: "Baixo risco", color: "#22c55e", bg: "bg-emerald-500" },
  some_concerns: { label: "Alguma preocupação", color: "#f59e0b", bg: "bg-amber-500" },
  high: { label: "Alto risco", color: "#ef4444", bg: "bg-red-500" },
} as const;

export const ROB2_SIGNAL = {
  Y: { label: "Sim", short: "S" },
  PY: { label: "Provavelmente sim", short: "PS" },
  PN: { label: "Provavelmente não", short: "PN" },
  N: { label: "Não", short: "N" },
  NI: { label: "Sem informação", short: "NI" },
} as const;

export const GRADE_CERTAINTY = {
  high: { label: "Alta", color: "text-emerald-700", bg: "bg-emerald-100", icon: "⊕⊕⊕⊕" },
  moderate: { label: "Moderada", color: "text-blue-700", bg: "bg-blue-100", icon: "⊕⊕⊕◯" },
  low: { label: "Baixa", color: "text-amber-700", bg: "bg-amber-100", icon: "⊕⊕◯◯" },
  very_low: { label: "Muito baixa", color: "text-red-700", bg: "bg-red-100", icon: "⊕◯◯◯" },
} as const;

export const GRADE_DOMAIN = {
  risk_of_bias: "Risco de viés",
  inconsistency: "Inconsistência",
  indirectness: "Evidência indireta",
  imprecision: "Imprecisão",
  publication_bias: "Viés de publicação",
} as const;

export const GRADE_RATING: Record<number, { label: string; color: string }> = {
  0: { label: "Sem rebaixamento", color: "text-emerald-600" },
  [-1]: { label: "Rebaixar -1", color: "text-amber-600" },
  [-2]: { label: "Rebaixar -2", color: "text-red-600" },
};

export const DOC_STATUS = {
  pending: { label: "Pendente", color: "text-zinc-500", dot: "bg-zinc-400" },
  fetched: { label: "Obtido", color: "text-blue-600", dot: "bg-blue-500" },
  extracted: { label: "Extraído", color: "text-emerald-600", dot: "bg-emerald-500" },
  failed: { label: "Falha", color: "text-red-600", dot: "bg-red-500" },
  requires_manual_transcription: { label: "Transcrição manual", color: "text-amber-600", dot: "bg-amber-500" },
} as const;

export const APPROVAL_STATUS = {
  draft: { label: "Rascunho", color: "text-zinc-600", bg: "bg-zinc-100" },
  approved: { label: "Aprovado", color: "text-emerald-600", bg: "bg-emerald-100" },
} as const;

export const IMPACT_TYPE = {
  novo_desfecho: { label: "Novo desfecho", color: "text-purple-600" },
  mudanca_direcao: { label: "Mudança de direção", color: "text-red-600" },
  mudanca_significancia: { label: "Mudança de significância", color: "text-amber-600" },
  mudanca_heterogeneidade: { label: "Mudança de heterogeneidade", color: "text-blue-600" },
  mudanca_certeza: { label: "Mudança de certeza", color: "text-orange-600" },
} as const;

export const FLOW_DISCREPANCY_LABEL: Record<string, string> = {
  records_in_db: "Identificados − duplicatas ≠ triados + pendentes",
  screening_balance: "Triados ≠ excluídos + full-text",
  fulltext_balance: "Full-text buscados ≠ não recuperados + avaliados",
  eligibility_balance: "Avaliados ≠ excluídos por motivo + incluídos",
};

export function lookupVocab<T extends Record<string, unknown>>(
  map: T,
  key: string,
  fallback?: { label: string; color: string },
): T[keyof T] {
  if (key in map) return map[key as keyof T];
  return (fallback ?? { label: key, color: "text-zinc-500" }) as T[keyof T];
}
