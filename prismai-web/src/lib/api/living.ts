import { apiFetch } from "./client";

export interface LivingUpdate {
  trigger?: string;
  search_sources?: string[];
  new_found?: number;
  new_imported?: number;
  new_duplicates?: number;
  screening_status?: string;
  impact_status?: string;
  impact_result?: {
    impacto: boolean;
    detalhes?: { outcome_key: string; tipo: string; descricao: string; antes?: number | null; depois?: number | null }[];
  } | null;
  notified?: boolean;
  created_at?: string | null;
}

export interface LivingStatus {
  enabled: boolean;
  cron?: string | null;
  total_updates: number;
  last_update?: LivingUpdate | null;
  pending_notifications: number;
}

export const livingApi = {
  enable: (reviewId: string, cron = "0 3 * * 1") =>
    apiFetch(`/v1/reviews/${reviewId}/living/enable`, { method: "POST", json: { cron } }),
  disable: (reviewId: string) =>
    apiFetch(`/v1/reviews/${reviewId}/living/disable`, { method: "POST" }),
  run: (reviewId: string, model = "gpt-4o-mini") =>
    apiFetch<{ job_id: string; status: string }>(`/v1/reviews/${reviewId}/living/run`, { method: "POST", json: { model } }),
  updates: (reviewId: string) =>
    apiFetch<LivingUpdate[]>(`/v1/reviews/${reviewId}/living/updates`),
  status: (reviewId: string) =>
    apiFetch<LivingStatus>(`/v1/reviews/${reviewId}/living/status`),
};
