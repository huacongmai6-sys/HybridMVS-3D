import { useState, useEffect } from "react";
import { getDepthPreviewUrl } from "../../api";
import "../../styles/results.css";

/**
 * DepthMapPanel — Depth map preview gallery + lightbox (dark theme).
 * Migrated from original DepthMapPanel.jsx, updated for dark theme.
 */
export default function DepthMapPanel({ depthPreviews, taskId }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  /* Reset when task changes */
  useEffect(() => {
    setExpandedIndex(null);
  }, [taskId]);

  if (!depthPreviews || depthPreviews.length === 0) return null;

  const handleKeyDown = (e) => {
    if (e.key === "Escape") setExpandedIndex(null);
    if (e.key === "ArrowRight" && expandedIndex !== null) {
      setExpandedIndex((expandedIndex + 1) % depthPreviews.length);
    }
    if (e.key === "ArrowLeft" && expandedIndex !== null) {
      setExpandedIndex(
        (expandedIndex - 1 + depthPreviews.length) % depthPreviews.length
      );
    }
  };

  return (
    <div className="depth-panel glass-card" onKeyDown={handleKeyDown} tabIndex={-1}>
      <h3 className="depth-panel-title text-mono">深度图预览</h3>
      <p className="depth-panel-desc text-muted">
        伪彩色深度估计中间结果，{depthPreviews.length} 张采样
      </p>

      <div className="depth-grid">
        {depthPreviews.slice(0, 5).map((preview, i) => (
          <button
            key={preview.filename}
            className="depth-thumb"
            onClick={() => setExpandedIndex(i)}
          >
            <img
              src={getDepthPreviewUrl(taskId, preview.filename)}
              alt={`深度图 ${preview.name}`}
              loading="lazy"
            />
            <span className="depth-label">{preview.name}</span>
            <span className="depth-range text-mono">
              {preview.min_depth?.toFixed(2)} – {preview.max_depth?.toFixed(2)}m
            </span>
          </button>
        ))}
      </div>

      {/* Lightbox */}
      {expandedIndex !== null && depthPreviews[expandedIndex] && (
        <div className="depth-lightbox" onClick={() => setExpandedIndex(null)}>
          <div className="depth-lightbox-content" onClick={(e) => e.stopPropagation()}>
            <img
              src={getDepthPreviewUrl(taskId, depthPreviews[expandedIndex].filename)}
              alt={`深度图 ${depthPreviews[expandedIndex].name}`}
            />
            <div className="depth-lightbox-info">
              <span>{depthPreviews[expandedIndex].name}</span>
              <span className="depth-range text-mono">
                深度范围: {depthPreviews[expandedIndex].min_depth?.toFixed(2)}m –{" "}
                {depthPreviews[expandedIndex].max_depth?.toFixed(2)}m
              </span>
              <span className="lightbox-index text-mono">
                {expandedIndex + 1} / {depthPreviews.length}
              </span>
            </div>
            <button className="lightbox-close" onClick={() => setExpandedIndex(null)}>
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
