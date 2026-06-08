import MetricsCards from "./MetricsCards";
import DepthMapPanel from "./DepthMapPanel";
import DownloadPanel from "./DownloadPanel";
import ComparisonView from "./ComparisonView";
import "../../styles/results.css";

/**
 * ResultsPanel — Aggregates all post-reconstruction result components.
 *
 * @param {{ completedTask: object, pointData: object|null }} props
 */
export default function ResultsPanel({ completedTask, pointData }) {
  if (!completedTask) return null;

  return (
    <div className="results-panel">
      {/* Success banner */}
      <div className="results-banner glass-card">
        <span className="results-emoji">&#127881;</span>
        <span className="results-banner-text">重建完成</span>
      </div>

      {/* Metrics */}
      <MetricsCards pointData={pointData} completedTask={completedTask} />

      {/* Depth maps */}
      {completedTask.depth_previews?.length > 0 && (
        <DepthMapPanel
          depthPreviews={completedTask.depth_previews}
          taskId={completedTask.id}
        />
      )}

      {/* Comparison */}
      {completedTask.sparse_ply && completedTask.dense_ply && (
        <ComparisonView
          taskId={completedTask.id}
          sparsePly={!!completedTask.sparse_ply}
          densePly={!!completedTask.dense_ply}
        />
      )}

      {/* Downloads */}
      <DownloadPanel
        taskId={completedTask.id}
        densePly={!!completedTask.dense_ply}
        denseObj={!!completedTask.dense_obj}
        sparsePly={!!completedTask.sparse_ply}
        stats={!!completedTask.stats_json}
      />
    </div>
  );
}
