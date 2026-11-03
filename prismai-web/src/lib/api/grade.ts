import { apiFetch } from "./client";

export interface GradeDomain {
  domain: string;
  rating: number;
  justificativa?: string;
  automatico?: boolean;
}

export interface GradeAssessment {
  outcome_key: string;
  starting_certainty?: string;
  domains: GradeDomain[];
  final_certainty: string;
  k_studies?: number;
  status?: string;
  degradado?: boolean;
  alertas?: string[];
}

export interface SofEntry {
  outcome_key: string;
  measure?: string;
  k_studies?: number;
  n_participants?: number | null;
  pooled_effect?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  certainty?: string;
  rob_downgrade?: number;
  inconsistency_downgrade?: number;
  indirectness_downgrade?: number;
  imprecision_downgrade?: number;
  pub_bias_downgrade?: number;
}

export const gradeApi = {
  run: (reviewId: string, model = "gpt-4o-mini") =>
    apiFetch<{ job_id: string; status: string }>(`/v1/reviews/${reviewId}/grade/run`, { method: "POST", json: { model } }),
  list: (reviewId: string) =>
    apiFetch<GradeAssessment[]>(`/v1/reviews/${reviewId}/grade`),
  approve: (reviewId: string, outcomeKey: string) =>
    apiFetch(`/v1/reviews/${reviewId}/grade/${outcomeKey}/approve`, { method: "POST" }),
  sof: (reviewId: string) =>
    apiFetch<{ entries: SofEntry[] }>(`/v1/reviews/${reviewId}/grade/sof`),
};
