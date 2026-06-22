import { useState, useRef } from "react";
import {
  uploadComparison,
  getComparison,
  getComparisonDownloadUrl,
} from "../api";
import ComparisonViewer from "../components/comparison/ComparisonViewer";
import "../styles/comparison.css";

// ── File upload zone ────────────────────────────────────────
function FileDropZone({ label, hint, icon, accepted, file, onFile, disabled }) {
  const inputRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    if (disabled) return;
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith(".ply")) onFile(f);
  };

  const handleChange = (e) => {
    if (e.target.files[0]) onFile(e.target.files[0]);
  };

  return (
    <div
      className={`comparison-drop-zone ${file ? "has-file" : ""} ${disabled ? "disabled" : ""}`}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <span className="drop-icon">{icon}</span>
      <span className="drop-label">{label}</span>
      {file ? (
        <span className="drop-filename">{file.name}</span>
      ) : (
        <span className="drop-hint">{hint}</span>
      )}
      <input
        ref={inputRef}
        type="file"
        accept=".ply"
        style={{ display: "none" }}
        onChange={handleChange}
      />
    </div>
  );
}

// ── Metric card ──────────────────────────────────────────────
function MetricCard({ label, value, unit, highlight }) {
  return (
    <div className={`metric-card ${highlight ? "highlight" : ""}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">
        {value ?? "—"}{unit && <span className="metric-unit">{unit}</span>}
      </span>
    </div>
  );
}

// ── F-score row ──────────────────────────────────────────────
function FScoreRow({ fScore }) {
  if (!fScore) return null;
  return (
    <div className="fscore-row">
      {Object.entries(fScore).map(([thresh, data]) => (
        <div key={thresh} className="fscore-item">
          <span className="fscore-threshold">{thresh}</span>
          <span className="fscore-value">{data.f1?.toFixed(4) ?? "—"}</span>
        </div>
      ))}
    </div>
  );
}

// ── Full metrics panel for one comparison ────────────────────
function MetricsPanel({ title, metrics, colorClass, isWinner }) {
  if (!metrics) {
    return (
      <div className={`metrics-panel ${colorClass}`}>
        <h3 className="metrics-title">{title}</h3>
        <p className="metrics-empty">等待对比…</p>
      </div>
    );
  }

  const m = metrics;
  const nc = m.normal_consistency != null
    ? (m.normal_consistency * 100).toFixed(1) + "%"
    : "N/A";

  return (
    <div className={`metrics-panel ${colorClass} ${isWinner ? "winner" : ""}`}>
      <h3 className="metrics-title">
        {title}
        {isWinner && <span className="winner-badge">BEST</span>}
      </h3>

      <div className="metrics-grid">
        <MetricCard label="① Chamfer Distance" value={m.chamfer_distance?.toFixed(6)} unit="m²" highlight />
        <MetricCard label="② Accuracy" value={m.accuracy_mm?.toFixed(2)} unit="mm" />
        <MetricCard label="   (median)" value={m.accuracy_median_mm?.toFixed(2)} unit="mm" />
        <MetricCard label="   Completeness" value={m.completeness_mm?.toFixed(2)} unit="mm" />
        <MetricCard label="   (median)" value={m.completeness_median_mm?.toFixed(2)} unit="mm" />
        <MetricCard label="③ F-score" value={null} />
      </div>

      <FScoreRow fScore={m.f_score} />

      <div className="metrics-grid metrics-grid-2">
        <MetricCard label="④ Outlier (pred)" value={m.outlier_ratio_pred != null ? (m.outlier_ratio_pred * 100).toFixed(2) + "%" : "—"} />
        <MetricCard label="   Outlier (GT)" value={m.outlier_ratio_gt != null ? (m.outlier_ratio_gt * 100).toFixed(2) + "%" : "—"} />
        <MetricCard label="⑤ Normal Consistency" value={nc} />
        <MetricCard label="Hausdorff Max" value={m.hausdorff_max_mm?.toFixed(2)} unit="mm" />
      </div>

      <div className="metrics-overall">
        <span className="overall-label">★ Overall Score</span>
        <span className="overall-value">
          {m.overall_score_mm?.toFixed(2)}<span className="metric-unit">mm</span>
        </span>
      </div>

      <div className="metrics-counts">
        <span>GT: {m.num_points_gt?.toLocaleString() ?? "—"} pts</span>
        <span>Pred: {m.num_points_pred?.toLocaleString() ?? "—"} pts</span>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────
export default function ComparisonPage({ onNavigate }) {
  const [gtFile, setGtFile] = useState(null);
  const [colmapFile, setColmapFile] = useState(null);
  const [mvsFile, setMvsFile] = useState(null);
  const [align, setAlign] = useState(false);
  const [estimateNormal, setEstimateNormal] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null); // { comparison: {...} }
  const [showViewer, setShowViewer] = useState(false);

  const handleSubmit = async () => {
    if (!gtFile || !colmapFile || !mvsFile) {
      setError("请上传全部 3 个 PLY 文件：基准(GT)、COLMAP、MVS");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await uploadComparison(gtFile, colmapFile, mvsFile, align, estimateNormal);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setGtFile(null);
    setColmapFile(null);
    setMvsFile(null);
    setResult(null);
    setError(null);
    setShowViewer(false);
  };

  const comparison = result?.comparison;
  const metrics = comparison?.metrics;
  const compId = comparison?.id;

  // Determine winner by overall score
  const colmapScore = metrics?.colmap_vs_gt?.overall_score_mm ?? Infinity;
  const mvsScore = metrics?.mvs_vs_gt?.overall_score_mm ?? Infinity;

  return (
    <div className="comparison-page">
      {/* ── Header ──────────────────────────────── */}
      <div className="comparison-header">
        <button className="back-btn" onClick={() => onNavigate?.("reconstruct")}>
          ← 返回
        </button>
        <h1 className="comparison-title">点云对比评估</h1>
        <span className="comparison-subtitle">
          Ground Truth · COLMAP Dense · MVS Network — 论文五件套指标
        </span>
      </div>

      <div className="comparison-body">
        {/* ── Upload Section ────────────────────── */}
        {!comparison && (
          <div className="comparison-upload-section glass-card">
            <div className="comparison-upload-zones">
              <FileDropZone
                label="🎯 Ground Truth (基准)"
                hint="拖入或点击选择基准 PLY"
                icon="🎯"
                accepted=".ply"
                file={gtFile}
                onFile={setGtFile}
                disabled={loading}
              />
              <FileDropZone
                label="🔵 COLMAP Dense"
                hint="拖入或点击选择 COLMAP PLY"
                icon="🔵"
                accepted=".ply"
                file={colmapFile}
                onFile={setColmapFile}
                disabled={loading}
              />
              <FileDropZone
                label="🟠 MVS Network"
                hint="拖入或点击选择 MVS PLY"
                icon="🟠"
                accepted=".ply"
                file={mvsFile}
                onFile={setMvsFile}
                disabled={loading}
              />
            </div>

            <div className="comparison-options">
              <label className="option-checkbox">
                <input
                  type="checkbox"
                  checked={align}
                  onChange={(e) => setAlign(e.target.checked)}
                  disabled={loading}
                />
                <span>ICP Alignment（自动配准坐标系）</span>
              </label>
              <label className="option-checkbox">
                <input
                  type="checkbox"
                  checked={estimateNormal}
                  onChange={(e) => setEstimateNormal(e.target.checked)}
                  disabled={loading}
                />
                <span>Normal Consistency（法向量一致性）</span>
              </label>
            </div>

            <div className="comparison-actions">
              <button
                className="btn-primary comparison-run-btn"
                disabled={loading || !gtFile || !colmapFile || !mvsFile}
                onClick={handleSubmit}
              >
                {loading ? "计算中…" : "开始对比"}
              </button>
              <button
                className="btn-secondary"
                disabled={loading}
                onClick={handleReset}
              >
                重置
              </button>
            </div>

            {error && <div className="comparison-error">{error}</div>}
          </div>
        )}

        {/* ── Results Section ───────────────────── */}
        {comparison && (
          <>
            {/* Result header */}
            <div className="result-header glass-card">
              <div className="result-header-left">
                <span className={`status-badge ${comparison.status}`}>
                  {comparison.status === "completed" ? "✓ 对比完成" : "✗ 对比失败"}
                </span>
                {comparison.status === "failed" && (
                  <span className="error-msg">{comparison.error_message}</span>
                )}
              </div>
              <div className="result-header-right">
                <button
                  className="btn-primary"
                  onClick={() => setShowViewer((v) => !v)}
                >
                  {showViewer ? "隐藏 3D 视图" : "查看 3D 对比"}
                </button>
                <button className="btn-secondary" onClick={handleReset}>
                  新建对比
                </button>
              </div>
            </div>

            {/* Metrics panels */}
            {metrics && (
              <div className="metrics-panels-row">
                <MetricsPanel
                  title="COLMAP vs Ground Truth"
                  metrics={metrics.colmap_vs_gt}
                  colorClass="colmap-panel"
                  isWinner={colmapScore < mvsScore}
                />
                <MetricsPanel
                  title="MVS vs Ground Truth"
                  metrics={metrics.mvs_vs_gt}
                  colorClass="mvs-panel"
                  isWinner={mvsScore < colmapScore}
                />
              </div>
            )}

            {/* COLMAP vs MVS auxiliary */}
            {metrics?.colmap_vs_mvs && (
              <div className="aux-metrics glass-card">
                <h4>辅助对比：COLMAP vs MVS</h4>
                <div className="aux-metrics-grid">
                  <span>CD: {metrics.colmap_vs_mvs.chamfer_distance?.toFixed(6)} m²</span>
                  <span>Acc: {metrics.colmap_vs_mvs.accuracy_mm?.toFixed(2)} mm</span>
                  <span>Com: {metrics.colmap_vs_mvs.completeness_mm?.toFixed(2)} mm</span>
                  <span>Overall: {metrics.colmap_vs_mvs.overall_score_mm?.toFixed(2)} mm</span>
                  <span>F1@2cm: {metrics.colmap_vs_mvs.f_score?.["0.02m"]?.f1?.toFixed(4) ?? "—"}</span>
                  <span>F1@5cm: {metrics.colmap_vs_mvs.f_score?.["0.05m"]?.f1?.toFixed(4) ?? "—"}</span>
                </div>
              </div>
            )}

            {/* 3D Viewer */}
            {showViewer && compId && (
              <div className="comparison-viewer-section glass-card">
                <ComparisonViewer
                  gtUrl={getComparisonDownloadUrl(compId, "gt_colored")}
                  colmapUrl={getComparisonDownloadUrl(compId, "colmap_colored")}
                  mvsUrl={getComparisonDownloadUrl(compId, "mvs_colored")}
                  gtColoredUrl={getComparisonDownloadUrl(compId, "gt_colored")}
                  colmapColoredUrl={getComparisonDownloadUrl(compId, "colmap_colored")}
                  mvsColoredUrl={getComparisonDownloadUrl(compId, "mvs_colored")}
                  metrics={metrics}
                />
              </div>
            )}

            {/* Downloads */}
            {compId && comparison.status === "completed" && (
              <div className="downloads-row glass-card">
                <h4>下载带距离颜色的点云</h4>
                <div className="downloads-btns">
                  <a
                    href={getComparisonDownloadUrl(compId, "gt_colored")}
                    className="btn-download"
                    download
                  >
                    📥 GT (colored)
                  </a>
                  <a
                    href={getComparisonDownloadUrl(compId, "colmap_colored")}
                    className="btn-download"
                    download
                  >
                    📥 COLMAP (colored)
                  </a>
                  <a
                    href={getComparisonDownloadUrl(compId, "mvs_colored")}
                    className="btn-download"
                    download
                  >
                    📥 MVS (colored)
                  </a>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
