import type { Paper } from "../lib/types";

import { StatusBadge } from "./StatusBadge";

interface PaperDetailProps {
  busy: boolean;
  loading: boolean;
  analyzeBusy: boolean;
  analyzeMessage: string | null;
  onAnalyze: () => void;
  onApprove: () => void;
  onReject: () => void;
  paper: Paper | null;
}

function formatDate(value: string) {
  return value.slice(0, 10);
}

export function PaperDetail({
  busy,
  loading,
  analyzeBusy,
  analyzeMessage,
  onAnalyze,
  onApprove,
  onReject,
  paper,
}: PaperDetailProps) {
  if (loading) {
    return (
      <div className="detail detail--state">
        {"\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0434\u0435\u0442\u0430\u043b\u0435\u0439 \u0441\u0442\u0430\u0442\u044c\u0438..."}
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="detail detail--state">
        {"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u0442\u0430\u0442\u044c\u044e \u0434\u043b\u044f \u0434\u0435\u0442\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430."}
      </div>
    );
  }

  const reviewDraft = paper.review_draft ?? null;
  const reviewActionsDisabled = busy || analyzeBusy || !reviewDraft;

  return (
    <section className="detail">
      <div className="detail__header">
        <div className="detail__headline">
          <p className="detail__eyebrow">Editorial review</p>
          <h2>{reviewDraft?.ru_title ?? paper.title}</h2>
        </div>
        <StatusBadge status={paper.status} />
      </div>

      {reviewDraft ? (
        <section className="detail__section detail__section--draft">
          <div className="detail__section-header">
            <h3>Review Draft</h3>
            <span className="detail__draft-state">Review Draft Ready</span>
          </div>
          <dl className="detail__draft-grid">
            <div className="detail__draft-block">
              <dt>RU Title</dt>
              <dd>{reviewDraft.ru_title}</dd>
            </div>
            <div className="detail__draft-block">
              <dt>RU Abstract</dt>
              <dd>{reviewDraft.ru_abstract}</dd>
            </div>
            <div className="detail__draft-block detail__draft-block--full">
              <dt>Summary</dt>
              <dd>{reviewDraft.summary}</dd>
            </div>
            <div className="detail__draft-block">
              <dt>Draft Model</dt>
              <dd>{reviewDraft.model_used ?? "\u2014"}</dd>
            </div>
          </dl>
        </section>
      ) : (
        <section className="detail__section detail__section--empty">
          <div className="detail__section-header">
            <h3>Review Draft</h3>
          </div>
          <p className="detail__hint">
            {"\u041f\u0435\u0440\u0435\u0434 \u0440\u0435\u0434\u0430\u043a\u0442\u043e\u0440\u0441\u043a\u043e\u0439 \u043e\u0446\u0435\u043d\u043a\u043e\u0439 \u043f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u044c\u0442\u0435 \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u0441\u043b\u043e\u0439 \u0441 \u043f\u043e\u043c\u043e\u0449\u044c\u044e Analyze Script."}
          </p>
        </section>
      )}

      <section className="detail__section">
        <div className="detail__section-header">
          <h3>Scoring</h3>
        </div>
        <dl className="detail__meta">
          <div>
            <dt>Final Score</dt>
            <dd>{paper.latest_score ? paper.latest_score.final_score.toFixed(1) : "\u2014"}</dd>
          </div>
          <div>
            <dt>Score Model</dt>
            <dd>{paper.latest_score?.model_used ?? "\u2014"}</dd>
          </div>
          <div>
            <dt>Published</dt>
            <dd>{formatDate(paper.published_at)}</dd>
          </div>
          <div>
            <dt>Source</dt>
            <dd>{paper.source}</dd>
          </div>
        </dl>
        {paper.latest_score?.explanation ? (
          <p className="detail__explanation">{paper.latest_score.explanation}</p>
        ) : null}
      </section>

      <section className="detail__section">
        <div className="detail__section-header">
          <h3>Original Source</h3>
        </div>
        <div className="detail__source">
          <h4>{paper.title}</h4>
          <p>{paper.abstract}</p>
        </div>
        <dl className="detail__meta">
          <div>
            <dt>Source ID</dt>
            <dd>{paper.source_id}</dd>
          </div>
          <div>
            <dt>Authors</dt>
            <dd>{paper.authors.join(", ") || "Unknown authors"}</dd>
          </div>
          <div>
            <dt>Categories</dt>
            <dd>{paper.categories.join(", ") || "\u2014"}</dd>
          </div>
          <div>
            <dt>PDF</dt>
            <dd>{paper.pdf_url ?? "\u2014"}</dd>
          </div>
        </dl>
      </section>

      <div className="detail__actions">
        <button type="button" onClick={onAnalyze} disabled={busy || analyzeBusy}>
          Analyze Script
        </button>
        <button type="button" onClick={onApprove} disabled={reviewActionsDisabled}>
          Approve
        </button>
        <button
          type="button"
          className="detail__reject"
          onClick={onReject}
          disabled={reviewActionsDisabled}
        >
          Reject
        </button>
      </div>

      {analyzeMessage ? (
        <p className={`detail__message${analyzeBusy ? "" : " detail__message--error"}`}>
          {analyzeMessage}
        </p>
      ) : null}
    </section>
  );
}
