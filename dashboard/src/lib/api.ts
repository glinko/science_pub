import type {
  CollectJobRequest,
  JobRecord,
  Paper,
  PaperListResponse,
  PaperStatus,
  ScoreJobRequest,
} from "./types";

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

export async function enqueueCollectJob(payload: CollectJobRequest): Promise<JobRecord> {
  const response = await fetch("/api/jobs/collect-arxiv", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("collect_job_failed");
  }

  return response.json() as Promise<JobRecord>;
}

export async function enqueueScoreJob(payload: ScoreJobRequest): Promise<JobRecord> {
  const response = await fetch("/api/jobs/score-papers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("score_job_failed");
  }

  return response.json() as Promise<JobRecord>;
}

export async function listJobs(): Promise<JobRecord[]> {
  const response = await fetch("/api/jobs");

  if (!response.ok) {
    throw new Error("jobs_list_failed");
  }

  return response.json() as Promise<JobRecord[]>;
}
