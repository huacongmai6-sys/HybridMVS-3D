import "../../styles/progress.css";

/**
 * ProgressBar — Gradient progress bar with glow and shine animation.
 * @param {{ percent: number, status: string }} props
 */
export default function ProgressBar({ percent = 0, status = "running" }) {
  const isFailed = status === "failed";
  const isDone = status === "completed";

  let barClass = "progress-bar-fill";
  if (isFailed) barClass += " failed";
  if (isDone) barClass += " done";

  return (
    <div className="progress-bar-wrap">
      <div className="progress-bar-track">
        <div
          className={barClass}
          style={{ width: `${Math.min(Math.max(percent, 0), 100)}%` }}
        />
      </div>
      <span className="progress-bar-pct text-mono">
        {Math.round(percent)}%
      </span>
    </div>
  );
}
