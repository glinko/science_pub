export interface Paper {
  id: string;
  title: string;
  score?: number;
}

export interface PaperListResponse {
  total: number;
  limit: number;
  offset: number;
  items: Paper[];
}
