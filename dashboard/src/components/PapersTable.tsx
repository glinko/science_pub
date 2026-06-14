import type { Paper } from "../lib/types";

import { StatusBadge } from "./StatusBadge";

interface PapersTableProps {
  papers: Paper[];
  selectedPaperId: string | null;
  onSelect: (paperId: string) => void;
}

function formatScore(paper: Paper) {
  return paper.latest_score ? paper.latest_score.final_score.toFixed(1) : "—";
}

function formatCategories(paper: Paper) {
  return paper.categories.length > 0 ? paper.categories.join(", ") : "—";
}

function formatPublishedDate(paper: Paper) {
  return paper.published_at.slice(0, 10);
}

export function PapersTable({ papers, selectedPaperId, onSelect }: PapersTableProps) {
  return (
    <div className="papers-table">
      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Source</th>
            <th>Published</th>
            <th>Categories</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          {papers.map((paper) => (
            <tr key={paper.id} className={paper.id === selectedPaperId ? "papers-table__row--selected" : undefined}>
              <td>
                <button
                  type="button"
                  className="papers-table__select"
                  onClick={() => onSelect(paper.id)}
                >
                  {paper.title}
                </button>
                <div className="papers-table__meta">{paper.authors.join(", ") || "Unknown authors"}</div>
              </td>
              <td>
                <StatusBadge status={paper.status} />
              </td>
              <td>{paper.source}</td>
              <td>{formatPublishedDate(paper)}</td>
              <td>{formatCategories(paper)}</td>
              <td>{formatScore(paper)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
