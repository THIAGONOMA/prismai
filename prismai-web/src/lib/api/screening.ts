import { apiFetch } from "./client";

export interface Decision {
  registro_id: string;
  decision: string;
  confidence: string;
  reasons: string[];
  evidence: string[];
  degradado?: boolean;
  alertas?: string[];
  screener?: string;
}

export interface Conflict {
  registro_id: string;
  decision_a: string;
  decision_b: string;
  screener_a: string;
  screener_b: string;
  disagreement_score: number;
  status: string;
  resolved_decision?: string | null;
  resolved_note?: string | null;
  resolved_at?: string | null;
}

export interface Agreement {
  kappa: number;
  n_total: number;
  n_agree: number;
  n_conflict: number;
}

export interface JobResponse {
  job_id: string;
  status: string;
  progress?: number;
  total?: number;
}

export const screeningApi = {
  run: (reviewId: string, model = "gpt-4o-mini") =>
    apiFetch<JobResponse>(`/v1/reviews/${reviewId}/screening/run`, { method: "POST", json: { model } }),
  decisions: (reviewId: string) =>
    apiFetch<Decision[]>(`/v1/reviews/${reviewId}/decisions`),
  conflicts: (reviewId: string) =>
    apiFetch<Conflict[]>(`/v1/reviews/${reviewId}/conflicts`),
  resolveConflict: (reviewId: string, registroId: string, decision: string, note = "") =>
    apiFetch(`/v1/reviews/${reviewId}/conflicts/${registroId}/resolve`, { method: "POST", json: { decision, note } }),
  agreement: (reviewId: string) =>
    apiFetch<Agreement>(`/v1/reviews/${reviewId}/agreement`),
};
