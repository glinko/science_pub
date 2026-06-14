import type { PaperListResponse } from "./types";

export async function listPapers(query: string): Promise<PaperListResponse> {
  const response = await fetch(`/api/papers?${query}`);

  if (!response.ok) {
    throw new Error("papers_list_failed");
  }

  return response.json() as Promise<PaperListResponse>;
}
