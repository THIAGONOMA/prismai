import { apiFetch, apiUrl } from "./client";

export interface FlowCounts {
  identificados_por_fonte: Record<string, number>;
  identificados_total: number;
  duplicatas_removidas: number;
  registros_triados: number;
  registros_excluidos: number;
  fulltext_buscados: number;
  fulltext_nao_recuperados: number;
  fulltext_avaliados: number;
  fulltext_excluidos_por_motivo: Record<string, number>;
  estudos_incluidos: number;
  triagem_pendente: number;
  conflitos_nao_resolvidos: number;
  discrepancias: {
    invariante: string;
    esperado: number;
    encontrado: number;
    detalhe?: string;
  }[];
}

export interface ChecklistItem {
  numero: string;
  secao: string;
  titulo: string;
  atendido: boolean;
  ponteiro?: string;
  nota?: string;
}

export interface ReportResult {
  kind?: string;
  status?: string;
  flow_counts?: Record<string, unknown> | null;
  discrepancies?: Record<string, unknown>[];
  checklist?: Record<string, unknown> | null;
  sections?: { key: string; titulo: string; corpo: string; flags?: string[] }[];
  approved_by?: string | null;
  approved_at?: string | null;
  degradado?: boolean;
  alertas?: string[];
}

export const reportApi = {
  flow: (reviewId: string) =>
    apiFetch<FlowCounts>(`/v1/reviews/${reviewId}/prisma-flow`),
  flowSvgUrl: (reviewId: string) =>
    apiUrl(`/v1/reviews/${reviewId}/prisma-flow.svg`),
  checklist: (reviewId: string) =>
    apiFetch<{ version: string; itens: ChecklistItem[]; n_atendidos: number }>(`/v1/reviews/${reviewId}/checklist`),
  run: (reviewId: string, model = "gpt-4o-mini") =>
    apiFetch<{ job_id: string; status: string }>(`/v1/reviews/${reviewId}/report/run`, { method: "POST", json: { model } }),
  get: (reviewId: string) =>
    apiFetch<ReportResult>(`/v1/reviews/${reviewId}/report`),
  approve: (reviewId: string) =>
    apiFetch(`/v1/reviews/${reviewId}/report/approve`, { method: "POST" }),
  downloadMd: (reviewId: string) => apiUrl(`/v1/reviews/${reviewId}/report.md`),
  downloadHtml: (reviewId: string) => apiUrl(`/v1/reviews/${reviewId}/report.html`),
  downloadDocx: (reviewId: string) => apiUrl(`/v1/reviews/${reviewId}/report.docx`),
  exportZip: (reviewId: string) => apiUrl(`/v1/reviews/${reviewId}/export`),
};
