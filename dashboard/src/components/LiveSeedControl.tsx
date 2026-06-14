import type { LiveSeedStage } from "../lib/types";

type LiveSeedControlProps = {
  busy: boolean;
  stage: LiveSeedStage;
  message: string | null;
  onRun: () => void;
};

export function LiveSeedControl({ busy, stage, message, onRun }: LiveSeedControlProps) {
  return (
    <div className="live-seed">
      <button type="button" className="live-seed__button" onClick={onRun} disabled={busy}>
        Fetch Fresh Papers
      </button>
      {stage !== "idle" && message ? (
        <p className={`live-seed__status live-seed__status--${stage}`}>{message}</p>
      ) : null}
    </div>
  );
}
