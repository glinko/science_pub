import type { PaperStatus } from "../lib/types";
import { paperStatusConfig } from "../lib/status";

export function StatusBadge({ status }: { status: PaperStatus }) {
  const config = paperStatusConfig[status];

  return (
    <span className={`status-badge status-badge--${config.tone}`}>
      {config.label}
    </span>
  );
}
