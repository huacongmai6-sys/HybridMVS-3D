import { useState } from "react";
import { getDepthPreviewUrl } from "../api";

/** Depth map preview gallery — shows 3-5 pseudo-colored depth maps. */
export default function DepthMapPanel({ depthPreviews, taskId }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!depthPreviews || depthPreviews.length === 0) return null;

  const handleKeyDown = (e) => {
    if (e.key === "Escape") setExpandedIndex(null);
    if (e.key === "ArrowRight" && expandedIndex !== null) {
      setExpandedIndex((expandedIndex + 1) % depthPreviews.length);
    }
    if (e.key === "ArrowLeft" && expandedIndex !== null) {
      setExpandedIndex((expandedIndex - 1 + depthPreviews.length) % depthPreviews.length);
    }
  };

  return (
    <div className="depth-panel" onKeyDown={handleKeyDown} tabIndex={-1}>
      <h3>深度图预览</h3>
      <p className="depth-panel-desc">
        深度估计中间结果（伪彩色，{depthPreviews.length}/{depthPreviews.length} 张采样）
      </p>

      <div className="depth-grid">
        {depthPreviews.slice(0, 5).map((preview, i) => (
          <button
            key={preview.filename}
            className="depth-thumb"
            onClick={() => setExpandedIndex(i)}
            title={`${preview.name} — 深度范围 [${preview.min_depth}, ${preview.max_depth}]`}
          >
            <img
              src={getDepthPreviewUrl(taskId, preview.filename)}
              alt={`深度图 ${preview.name}`}
              loading="lazy"
            />
            <span className="depth-label">{preview.name}</span>
            <span className="depth-range">
              {preview.min_depth}m – {preview.max_depth}m
            </span>
          </button>
        ))}
      </div>

      {/* Lightbox overlay */}
      {expandedIndex !== null && depthPreviews[expandedIndex] && (
        <div className="depth-lightbox" onClick={() => setExpandedIndex(null)}>
          <div className="depth-lightbox-content" onClick={(e) => e.stopPropagation()}>
            <img
              src={getDepthPreviewUrl(taskId, depthPreviews[expandedIndex].filename)}
              alt={`深度图 ${depthPreviews[expandedIndex].name}`}
            />
            <div className="depth-lightbox-info">
              <span>{depthPreviews[expandedIndex].name}</span>
              <span className="depth-range">
                深度范围: {depthPreviews[expandedIndex].min_depth}m –{" "}
                {depthPreviews[expandedIndex].max_depth}m
              </span>
              <span className="lightbox-index">
                {expandedIndex + 1} / {depthPreviews.length}
              </span>
            </div>
            <button
              className="lightbox-close"
              onClick={() => setExpandedIndex(null)}
            >
              ✕
            </button>
            {depthPreviews.length > 1 && (
              <>
                <button
                  className="lightbox-nav lightbox-prev"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedIndex(
                      (expandedIndex - 1 + depthPreviews.length) % depthPreviews.length
                    );
                  }}
                >
                  ‹
                </button>
                <button
                  className="lightbox-nav lightbox-next"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedIndex((expandedIndex + 1) % depthPreviews.length);
                  }}
                >
                  ›
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
