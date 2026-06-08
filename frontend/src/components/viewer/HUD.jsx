import { formatCount, formatDuration } from "../../utils/formatters";
import "../../styles/viewer.css";

/**
 * HUD — Floating overlay displaying point cloud stats and controls.
 *
 * @param {{ pointData: object|null, loading: boolean, error: string|null,
 *            stats: object|null, colorMode: string, onColorModeChange: function,
 *            autoRotate: boolean, onAutoRotateToggle: function }} props
 */
export default function HUD({
  pointData,
  loading,
  error,
  stats,
  colorMode,
  onColorModeChange,
  autoRotate,
  onAutoRotateToggle,
}) {
  return (
    <>
      {/* ── Top-left: status badge ────────────── */}
      <div className="hud-top">
        {loading && (
          <div className="hud-badge">
            <span className="status-dot primary" style={{ animation: "dotPulse 1.5s ease infinite" }} />
            加载中…
          </div>
        )}
        {error && (
          <div className="hud-badge error">
            <span className="status-dot error" />
            加载失败: {error}
          </div>
        )}
        {pointData && !loading && !error && (
          <div className="hud-badge ready">
            <span className="status-dot success" />
            就绪
          </div>
        )}
      </div>

      {/* ── Bottom-left: color mode selector ───── */}
      <div className="hud-bottom-left">
        <div className="color-mode-selector">
          {[
            { id: "rgb", label: "RGB", icon: "◉" },
            { id: "depth", label: "深度", icon: "⇅" },
            { id: "confidence", label: "置信度", icon: "✓", disabled: true },
          ].map((mode) => (
            <button
              key={mode.id}
              className={`color-mode-btn${colorMode === mode.id ? " active" : ""}${mode.disabled ? " disabled" : ""}`}
              onClick={() => !mode.disabled && onColorModeChange(mode.id)}
              title={mode.disabled ? "置信度数据暂不可用" : `${mode.label} 模式`}
              disabled={mode.disabled}
            >
              <span className="color-mode-icon">{mode.icon}</span>
              <span className="color-mode-label">{mode.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Bottom-right: stats panel ──────────── */}
      {pointData && !loading && !error && (
        <div className="hud-stats glass-card">
          <div className="hud-stat">
            <span className="hud-stat-label">顶点</span>
            <span className="hud-stat-value text-mono">{formatCount(pointData.count)}</span>
          </div>
          <span className="hud-stat-divider" />
          <div className="hud-stat">
            <span className="hud-stat-label">范围</span>
            <span className="hud-stat-value text-mono">{pointData.extent.toFixed(2)}</span>
          </div>
          {stats?.num_images && (
            <>
              <span className="hud-stat-divider" />
              <div className="hud-stat">
                <span className="hud-stat-label">图片</span>
                <span className="hud-stat-value text-mono">{stats.num_images}</span>
              </div>
            </>
          )}
          {stats?.duration && (
            <>
              <span className="hud-stat-divider" />
              <div className="hud-stat">
                <span className="hud-stat-label">耗时</span>
                <span className="hud-stat-value text-mono">{formatDuration(stats.duration)}</span>
              </div>
            </>
          )}
          <span className="hud-stat-divider" />
          <button
            className={`hud-auto-rotate${autoRotate ? " active" : ""}`}
            onClick={onAutoRotateToggle}
            title={autoRotate ? "停止自动旋转" : "自动旋转"}
          >
            {autoRotate ? "⟳ 旋转中" : "↻ 旋转"}
          </button>
        </div>
      )}
    </>
  );
}
