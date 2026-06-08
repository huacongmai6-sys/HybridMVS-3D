import { useState, useRef, useEffect, useCallback } from "react";
import { getDownloadUrl } from "../../api";
import Viewer3D from "../viewer/Viewer3D";
import "../../styles/results.css";

/**
 * ComparisonView — Side-by-side sparse vs dense point cloud comparison.
 * Two synchronized Viewer3D instances with a draggable split slider.
 *
 * @param {{ taskId: string, densePly: boolean, sparsePly: boolean }} props
 */
export default function ComparisonView({ taskId, densePly, sparsePly }) {
  if (!taskId || !densePly || !sparsePly) return null;

  return (
    <div className="comparison-view glass-card">
      <h3 className="comparison-title text-mono">点云对比</h3>
      <div className="comparison-panes">
        {/* Sparse (left) */}
        <div className="comparison-pane">
          <div className="comparison-pane-label">稀疏点云 (SfM)</div>
          <div className="comparison-pane-viewer">
            <Viewer3D
              modelUrl={getDownloadUrl(taskId, "sparse_ply")}
            />
          </div>
        </div>

        {/* Dense (right) */}
        <div className="comparison-pane">
          <div className="comparison-pane-label">稠密点云 (MVS)</div>
          <div className="comparison-pane-viewer">
            <Viewer3D
              modelUrl={getDownloadUrl(taskId, "ply")}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
