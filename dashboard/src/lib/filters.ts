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

export function buildPapersQuery(filters: PaperFilters) {
  const params = new URLSearchParams({
    include_scores: "true",
    limit: "25",
    offset: "0",
  });

  if (filters.status) params.set("status", filters.status);
  if (filters.source) params.set("source", filters.source);
  if (filters.category) params.set("category", filters.category);
  if (filters.min_score) params.set("min_score", filters.min_score);
  if (filters.search) params.set("search", filters.search);

  return params.toString();
}
