import { apiFetch } from "./client";

export interface SearchResponse {
  imported: number;
  duplicates: number;
  total_found: number;
}

export interface ImportRunResponse {
  source: string;
  total_found: number;
  imported: number;
  duplicates: number;
  created_at?: string;
}

export const searchApi = {
  run: (reviewId: string, query: string, source = "openalex", maxResults = 200) =>
    apiFetch<SearchResponse>(`/v1/reviews/${reviewId}/search`, {
      method: "POST", json: { source, query, max_results: maxResults },
    }),
  importFile: (reviewId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch<{ imported: number; duplicates: number; format: string }>(
      `/v1/reviews/${reviewId}/import`, { method: "POST", body: form },
    );
  },
  importRuns: (reviewId: string) =>
    apiFetch<ImportRunResponse[]>(`/v1/reviews/${reviewId}/import-runs`),
};
