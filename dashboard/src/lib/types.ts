export type PaperStatus =
  | "collected"
  | "scored"
  | "selected"
  | "analyzed"
  | "scripted"
  | "assets_ready"
  | "rendered"
  | "approved"
  | "rejected"
  | "published"
  | "failed";

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export type LiveSeedStage = "idle" | "collecting" | "scoring" | "success" | "failed";

export interface LatestScore {
  final_score: number;
  explanation: string;
  model_used: string;
  created_at: string;
}

export interface ReviewDraft {
  ru_title: string;
  ru_abstract: string;
  summary: string;
  model_used: string | null;
}

export interface Paper {
  id: string;
  source: string;
  source_id: string;
  title: string;
  abstract: string;
  authors: string[];
  categories: string[];
  pdf_url: string | null;
  published_at: string;
  collected_at: string;
  status: PaperStatus;
  raw_metadata_json: Record<string, unknown>;
  latest_score: LatestScore | null;
  review_draft?: ReviewDraft | null;
}

export interface PaperListResponse {
  total: number;
  limit: number;
  offset: number;
  items: Paper[];
}

export interface JobRecord {
  id: string;
  job_type: string;
  status: JobStatus;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown> | null;
  error_text: string | null;
  created_at: string;
  updated_at: string;
}

export interface CollectJobRequest {
  categories: string[];
  max_results: number;
}

export interface ScoreJobRequest {
  limit: number;
  status: PaperStatus;
  provider: string;
}

export interface AnalyzeScriptJobRequest {
  paper_id: string;
  limit?: number;
  status?: PaperStatus;
  provider?: string;
}
