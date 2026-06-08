import { useState } from "react";
import { useAppContext } from "../../context/AppContext";
import "../../styles/upload.css";

export default function AdvancedSettings() {
  const [expanded, setExpanded] = useState(false);
  const { advancedSettings, setAdvancedSettings } = useAppContext();

  const update = (key, value) => {
    setAdvancedSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="advanced-settings glass-card">
      <button
        className="settings-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="settings-toggle-left">
          <svg
            className={`settings-chevron${expanded ? " open" : ""}`}
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
          <span>高级设置</span>
        </div>
        {!expanded && (
          <span className="settings-summary text-muted">
            图片 {advancedSettings.imageResize}px · 置信度 {advancedSettings.confidenceThreshold}
          </span>
        )}
      </button>

      {expanded && (
        <div className="settings-panel">
          {/* Depth range */}
          <div className="settings-field">
            <label className="settings-label">深度范围 (m)</label>
            <div className="settings-row">
              <input
                type="number"
                className="settings-input"
                placeholder="最小 (自动)"
                value={advancedSettings.depthMin ?? ""}
                onChange={(e) => update("depthMin", e.target.value ? parseFloat(e.target.value) : null)}
              />
              <span className="settings-sep">—</span>
              <input
                type="number"
                className="settings-input"
                placeholder="最大 (自动)"
                value={advancedSettings.depthMax ?? ""}
                onChange={(e) => update("depthMax", e.target.value ? parseFloat(e.target.value) : null)}
              />
            </div>
            <span className="settings-hint">留空则自动估算</span>
          </div>

          {/* Image resize */}
          <div className="settings-field">
            <label className="settings-label">
              图片最大尺寸: <strong>{advancedSettings.imageResize}px</strong>
            </label>
            <input
              type="range"
              min="800"
              max="4000"
              step="100"
              value={advancedSettings.imageResize}
              onChange={(e) => update("imageResize", parseInt(e.target.value))}
              className="settings-slider"
            />
            <div className="settings-range-labels">
              <span>800</span>
              <span>4000</span>
            </div>
          </div>

          {/* Confidence threshold (MVS only) */}
          <div className="settings-field">
            <label className="settings-label">
              置信度阈值: <strong>{advancedSettings.confidenceThreshold.toFixed(2)}</strong>
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={advancedSettings.confidenceThreshold}
              onChange={(e) => update("confidenceThreshold", parseFloat(e.target.value))}
              className="settings-slider"
            />
            <div className="settings-range-labels">
              <span>0.00</span>
              <span>1.00</span>
            </div>
            <span className="settings-hint">仅 MVS 模式生效</span>
          </div>

          {/* Voxel size */}
          <div className="settings-field">
            <label className="settings-label">体素尺寸 (cm)</label>
            <input
              type="number"
              className="settings-input"
              placeholder="自动计算"
              value={advancedSettings.voxelSize ?? ""}
              onChange={(e) => update("voxelSize", e.target.value ? parseFloat(e.target.value) : null)}
            />
            <span className="settings-hint">留空则自动</span>
          </div>
        </div>
      )}
    </div>
  );
}
