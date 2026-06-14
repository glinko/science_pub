export type PaperFilters = {
  status: string;
  source: string;
  category: string;
  min_score: string;
  search: string;
};

export const defaultPaperFilters: PaperFilters = {
  status: "",
  source: "",
  category: "",
  min_score: "",
  search: "",
};

export function isMinScoreValid(value: string) {
  const trimmed = value.trim();

  if (!trimmed) {
    return true;
  }

  const parsed = Number(trimmed);
  return Number.isFinite(parsed);
}

function normalizeMinScore(value: string) {
  const trimmed = value.trim();

  if (!trimmed) {
    return "";
  }

  return isMinScoreValid(trimmed) ? trimmed : null;
}

export function buildPapersQuery(filters: PaperFilters) {
  const params = new URLSearchParams({
    include_scores: "true",
    limit: "25",
    offset: "0",
  });

  if (filters.status) params.set("status", filters.status);
  if (filters.source) params.set("source", filters.source);
  if (filters.category) params.set("category", filters.category);
  const minScore = normalizeMinScore(filters.min_score);
  if (minScore) params.set("min_score", minScore);
  if (filters.search) params.set("search", filters.search);

  return params.toString();
}
