import { apiFetch } from "./client";

export interface ExtractionCell {
  field: string;
  block: string;
  value: unknown;
  value_type?: string;
  page?: number | null;
  start_offset?: number | null;
  end_offset?: number | null;
  evidence_text?: string | null;
  confidence?: string;
  needs_human_confirmation?: boolean;
  flags?: string[];
}

export interface Extraction {
  record_id: string;
  schema_version?: string;
  status?: string;
  cells: ExtractionCell[];
  consistency_flags?: string[];
  degradado?: boolean;
  alertas?: string[];
}

export interface RobAssessment {
  record_id: string;
  instrument?: string;
  overall_judgment: string;
  domain_results: {
    domain: string;
    judgment: string;
    signalling_questions?: { question: string; answer: string }[];
  }[];
  degradado?: boolean;
  alertas?: string[];
}

export const extractionApi = {
  run: (reviewId: string, model = "gpt-4o-mini") =>
    apiFetch<{ job_id: string; status: string }>(`/v1/reviews/${reviewId}/extraction/run`, { method: "POST", json: { model } }),
  get: (reviewId: string, recordId: string) =>
    apiFetch<Extraction>(`/v1/reviews/${reviewId}/extraction/${recordId}`),
  list: (reviewId: string) =>
    apiFetch<Extraction[]>(`/v1/reviews/${reviewId}/extractions`),
  robRun: (reviewId: string, model = "gpt-4o-mini") =>
    apiFetch<{ job_id: string; status: string }>(`/v1/reviews/${reviewId}/rob/run`, { method: "POST", json: { model } }),
  robList: (reviewId: string) =>
    apiFetch<RobAssessment[]>(`/v1/reviews/${reviewId}/rob`),
};
