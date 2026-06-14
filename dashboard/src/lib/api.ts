import type { PaperListResponse } from "./types";

export interface ListPapersParams {
  include_scores?: boolean;
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
