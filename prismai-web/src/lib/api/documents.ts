import { apiFetch } from "./client";

export interface Document {
  record_id: string;
  status: string;
  fetch_source?: string | null;
  n_pages?: number;
  ocr_confidence?: number | null;
  extraction_method?: string | null;
  error?: string | null;
}

export interface EligibilityDecision {
  document_id?: string | null;
  decision: string;
  exclusion_reason?: string | null;
  confidence: string;
  reasons?: string[];
  degradado?: boolean;
  alertas?: string[];
}

export const documentsApi = {
  list: (reviewId: string) =>
    apiFetch<Document[]>(`/v1/reviews/${reviewId}/documents`),
  fetchFulltext: (reviewId: string) =>
    apiFetch<{ job_id: string; status: string }>(`/v1/reviews/${reviewId}/fulltext/fetch`, { method: "POST" }),
  upload: (reviewId: string, recordId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch(`/v1/reviews/${reviewId}/documents/${recordId}/upload`, { method: "POST", body: form });
  },
  runEligibility: (reviewId: string, model = "gpt-4o-mini") =>
    apiFetch<{ job_id: string; status: string }>(`/v1/reviews/${reviewId}/eligibility/run`, { method: "POST", json: { model } }),
  eligibilityDecisions: (reviewId: string) =>
    apiFetch<EligibilityDecision[]>(`/v1/reviews/${reviewId}/eligibility/decisions`),
};
