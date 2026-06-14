import type { PaperListResponse, PaperStatus } from "./types";

export type ListPapersSortBy = "published_at" | "collected_at" | "title";
export type ListPapersSortOrder = "asc" | "desc";

export interface ListPapersParams {
  limit?: number;
  offset?: number;
  source?: string;
  category?: string;
  published_from?: string;
  published_to?: string;
  status?: PaperStatus;
  min_score?: number;
  include_scores?: boolean;
  search?: string;
  sort_by?: ListPapersSortBy;
  sort_order?: ListPapersSortOrder;
}

export async function listPapers(params: ListPapersParams): Promise<PaperListResponse> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }

  const response = await fetch(`/api/papers?${query.toString()}`);
  if (!response.ok) {
    throw new Error("papers_list_failed");
  }

  return response.json() as Promise<PaperListResponse>;
}
