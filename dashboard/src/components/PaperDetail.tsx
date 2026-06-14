import type { Paper } from "../lib/types";

import { StatusBadge } from "./StatusBadge";

interface PaperDetailProps {
  busy: boolean;
  loading: boolean;
  onApprove: () => void;
  onReject: () => void;
  paper: Paper | null;
}

function formatDate(value: string) {
  return value.slice(0, 10);
}

export function PaperDetail({ busy, loading, onApprove, onReject, paper }: PaperDetailProps) {
  if (loading) {
    return <div className="detail detail--state">Загрузка деталей статьи...</div>;
  }

  if (!paper) {
    return <div className="detail detail--state">Выберите статью для детального просмотра.</div>;
  }

  return (
    <section className="detail">
      <div className="detail__header">
        <h2>{paper.title}</h2>
        <StatusBadge status={paper.status} />
      </div>
      <p className="detail__abstract">{paper.abstract}</p>
      <dl className="detail__meta">
        <div>
          <dt>Source</dt>
          <dd>{paper.source}</dd>
        </div>
        <div>
          <dt>Source ID</dt>
          <dd>{paper.source_id}</dd>
        </div>
        <div>
          <dt>Published</dt>
          <dd>{formatDate(paper.published_at)}</dd>
        </div>
        <div>
          <dt>Authors</dt>
          <dd>{paper.authors.join(", ") || "Unknown authors"}</dd>
        </div>
        <div>
          <dt>Categories</dt>
          <dd>{paper.categories.join(", ") || "—"}</dd>
        </div>
        <div>
          <dt>Score</dt>
          <dd>{paper.latest_score ? paper.latest_score.final_score.toFixed(1) : "—"}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{paper.latest_score?.model_used ?? "—"}</dd>
        </div>
      </dl>
      <div className="detail__actions">
        <button type="button" onClick={onApprove} disabled={busy}>
          Approve
        </button>
        <button type="button" className="detail__reject" onClick={onReject} disabled={busy}>
          Reject
        </button>
      </div>
    </section>
  );
}
