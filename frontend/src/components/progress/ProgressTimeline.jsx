import {
  getTimelineStep,
  TIMELINE_STEPS,
  STAGE_NAMES,
} from "../../hooks/useTaskPolling";
import "../../styles/progress.css";

/**
 * ProgressTimeline — 7-stage vertical timeline visualization.
 * @param {{ stage: string, status: string, progress: number }} task snapshot
 */
export default function ProgressTimeline({ stage, status, progress }) {
  const currentStep = getTimelineStep(stage);
  const isFailed = status === "failed";
  const isDone = status === "completed";

  return (
    <div className="progress-timeline glass-card">
      <h3 className="timeline-title text-mono">重建进度</h3>
      <div className="timeline">
        {TIMELINE_STEPS.map((item, i) => {
          const stepNum = item.step;
          let state = "pending"; /* pending | active | done | failed */

          if (isFailed && stepNum === currentStep) {
            state = "failed";
          } else if (isDone) {
            state = "done";
          } else if (stepNum < currentStep) {
            state = "done";
          } else if (stepNum === currentStep) {
            state = "active";
          }

          return (
            <div key={stepNum} className={`timeline-node ${state}`}>
              {/* Connector line (not for last) */}
              {i < TIMELINE_STEPS.length - 1 && (
                <div className={`timeline-connector ${state === "done" ? "done" : ""}`} />
              )}

              {/* Node icon */}
              <div className="timeline-dot">
                {state === "done" && (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" strokeWidth="3" strokeLinecap="round"
                       strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
                {state === "failed" && (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                )}
                {state === "active" && <span className="timeline-dot-pulse" />}
                {state === "pending" && <span className="timeline-dot-empty" />}
              </div>

              {/* Label */}
              <div className="timeline-node-label">
                <span className="timeline-step-name">{item.label}</span>
                {state === "active" && (
                  <span className="timeline-step-status">
                    {STAGE_NAMES[stage] || stage || "处理中..."} · {progress}%
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
