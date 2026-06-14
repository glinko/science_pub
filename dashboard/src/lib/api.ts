import type { Paper, PaperListResponse, PaperStatus } from "./types";

export async function listPapers(query: string): Promise<PaperListResponse> {
  const response = await fetch(`/api/papers?${query}`);

  if (!response.ok) {
    throw new Error("papers_list_failed");
  }

  return response.json() as Promise<PaperListResponse>;
}

export async function getPaper(paperId: string): Promise<Paper> {
  const response = await fetch(`/api/papers/${paperId}`);

  if (!response.ok) {
    throw new Error("paper_detail_failed");
  }

  return response.json() as Promise<Paper>;
}

export async function updatePaperStatus(paperId: string, status: PaperStatus): Promise<Paper> {
  const response = await fetch(`/api/papers/${paperId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });

  if (!response.ok) {
    throw new Error("paper_status_failed");
  }

  return response.json() as Promise<Paper>;
}
