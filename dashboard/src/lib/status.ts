import type { PaperStatus } from "./types";

export type StatusTone = "neutral" | "info" | "accent" | "success" | "danger" | "warning";

export interface PaperStatusConfig {
  label: string;
  tone: StatusTone;
}

export const paperStatusConfig: Record<PaperStatus, PaperStatusConfig> = {
  approved: { label: "Approved", tone: "success" },
  analyzed: { label: "Analyzed", tone: "accent" },
  assets_ready: { label: "Assets Ready", tone: "info" },
  collected: { label: "Collected", tone: "info" },
  failed: { label: "Failed", tone: "danger" },
  published: { label: "Published", tone: "success" },
  rejected: { label: "Rejected", tone: "danger" },
  rendered: { label: "Rendered", tone: "warning" },
  scored: { label: "Scored", tone: "accent" },
  scripted: { label: "Scripted", tone: "warning" },
  selected: { label: "Selected", tone: "neutral" },
};

export const paperStatusOptions = Object.entries(paperStatusConfig) as Array<
  [PaperStatus, PaperStatusConfig]
>;
