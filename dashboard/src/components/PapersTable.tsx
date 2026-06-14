import type { Paper } from "../lib/types";

import { StatusBadge } from "./StatusBadge";

interface PapersTableProps {
  papers: Paper[];
}

function formatScore(paper: Paper) {
  return paper.latest_score ? paper.latest_score.final_score.toFixed(1) : "—";
}

function formatCategories(paper: Paper) {
  return paper.categories.length > 0 ? paper.categories.join(", ") : "—";
}

export function PapersTable({ papers }: PapersTableProps) {
  return (
    <div className="papers-table">
      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Source</th>
            <th>Categories</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          {papers.map((paper) => (
            <tr key={paper.id}>
              <td>
                <div className="papers-table__title">{paper.title}</div>
                <div className="papers-table__meta">{paper.authors.join(", ") || "Unknown authors"}</div>
              </td>
              <td>
                <StatusBadge status={paper.status} />
              </td>
              <td>{paper.source}</td>
              <td>{formatCategories(paper)}</td>
              <td>{formatScore(paper)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
