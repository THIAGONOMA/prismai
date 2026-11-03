import { apiFetch } from "./client";

export interface StudyEffect {
  record_id: string;
  incluido?: boolean;
  yi?: number | null;
  vi?: number | null;
  se?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  weight_fixed?: number | null;
  weight_random?: number | null;
  n_total?: number | null;
  rob?: string | null;
}

export interface SynthesisResult {
  outcome_key: string;
  measure?: string;
  model?: string;
  k_studies?: number;
  pooled_effect?: number | null;
  se?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  p_value?: number | null;
  tau2?: number | null;
  i2?: number | null;
  study_effects?: StudyEffect[];
  status?: string;
  degradado?: boolean;
  alertas?: string[];
}

export interface ForestData {
  studies: {
    label: string;
    yi: number;
    ci_low: number;
    ci_high: number;
    weight: number;
    incluido: boolean;
  }[];
  pooled: { yi: number; ci_low: number; ci_high: number };
  measure: string;
  model: string;
  i2: number;
  tau2: number;
}

export interface FunnelData {
  points: { yi: number; se: number }[];
  pooled: number;
}

export const synthesisApi = {
  setConfig: (reviewId: string, config: Record<string, unknown>) =>
    apiFetch(`/v1/reviews/${reviewId}/synthesis/config`, { method: "POST", json: { config } }),
  getConfig: (reviewId: string) =>
    apiFetch<Record<string, unknown>>(`/v1/reviews/${reviewId}/synthesis/config`),
  run: (reviewId: string, model = "gpt-4o-mini") =>
    apiFetch<{ job_id: string; status: string }>(`/v1/reviews/${reviewId}/synthesis/run`, { method: "POST", json: { model } }),
  list: (reviewId: string) =>
    apiFetch<SynthesisResult[]>(`/v1/reviews/${reviewId}/synthesis`),
  get: (reviewId: string, outcomeKey: string) =>
    apiFetch<SynthesisResult>(`/v1/reviews/${reviewId}/synthesis/${outcomeKey}`),
  approve: (reviewId: string, outcomeKey: string) =>
    apiFetch(`/v1/reviews/${reviewId}/synthesis/${outcomeKey}/approve`, { method: "POST" }),
  forest: (reviewId: string, outcomeKey: string) =>
    apiFetch<ForestData>(`/v1/reviews/${reviewId}/synthesis/${outcomeKey}/forest`),
  funnel: (reviewId: string, outcomeKey: string) =>
    apiFetch<FunnelData>(`/v1/reviews/${reviewId}/synthesis/${outcomeKey}/funnel`),
};
