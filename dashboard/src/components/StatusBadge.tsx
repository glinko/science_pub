import type { PaperStatus } from "../lib/types";

const statusLabels: Partial<Record<PaperStatus, string>> = {
  approved: "Approved",
  collected: "Collected",
  rejected: "Rejected",
  scored: "Scored",
};

export function StatusBadge({ status }: { status: PaperStatus }) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      {statusLabels[status] ?? status}
    </span>
  );
}
