import { apiFetch } from "./client";

export interface Review {
  id: string;
  created_at?: string;
  living_enabled?: boolean;
  living_cron?: string | null;
}

export interface Protocol {
  pergunta: string;
  P: string;
  I: string;
  C: string;
  O: string;
  desenho: string;
  inclusao: string[];
  exclusao: string[];
}

export const reviewsApi = {
  list: () => apiFetch<Review[]>("/v1/reviews"),
  get: (id: string) => apiFetch<Review>(`/v1/reviews/${id}`),
  create: (id: string) => apiFetch<Review>("/v1/reviews", { method: "POST", json: { id } }),
  getProtocol: (id: string) => apiFetch<Protocol>(`/v1/reviews/${id}/protocol`),
  setProtocol: (id: string, p: Protocol) => apiFetch(`/v1/reviews/${id}/protocol`, { method: "POST", json: p }),
  getDecisions: (id: string) => apiFetch<unknown[]>(`/v1/reviews/${id}/decisions`),
};
