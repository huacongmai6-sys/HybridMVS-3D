import { useState, useEffect, useRef } from "react";
import { getDownloadUrl } from "../../api";
import { parsePLY } from "../../utils/plyParser";
import Scene from "./Scene";
import HUD from "./HUD";
import "../../styles/viewer.css";

/**
 * Viewer3D — Loads & parses a PLY, renders 3D scene with HUD overlays.
 *
 * @param {{ modelUrl: string|null, sparseUrl: string|null, stats: object|null }} props
 */
export default function Viewer3D({ modelUrl, sparseUrl, stats }) {
  const [pointData, setPointData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [colorMode, setColorMode] = useState("rgb");
  const [autoRotate, setAutoRotate] = useState(false);
  const orbitRef = useRef(null);

  /* ── Auto-rotate via OrbitControls ref ─────── */
  useEffect(() => {
    if (orbitRef.current) {
      orbitRef.current.autoRotate = autoRotate;
      orbitRef.current.autoRotateSpeed = 0.6;
    }
  }, [autoRotate]);

  /* ── Load & parse PLY ──────────────────────── */
  useEffect(() => {
    if (!modelUrl) {
      setPointData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    fetch(modelUrl)
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      })
      .then((text) => {
        if (!active) return;
        const data = parsePLY(text);
        if (data.count === 0) {
          setError("点云为空 — 没有有效顶点数据");
          return;
        }
        setPointData(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [modelUrl]);

  /* ── Placeholder state ─────────────────────── */
  if (!modelUrl) {
    return (
      <div className="viewer-placeholder">
        <div className="placeholder-icon">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"
               strokeLinejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </div>
        <p>上传图片或视频并开始重建<br />三维模型将在此处显示</p>
        <span className="placeholder-hint">
          支持 PLY 稠密点云 · 旋转 / 缩放 / 平移
        </span>
      </div>
    );
  }

  return (
    <div className="viewer-3d">
      {/* ── Three.js Canvas ───────────────────── */}
      <Scene
        pointData={pointData}
        colorMode={colorMode}
        orbitRef={orbitRef}
        autoRotate={autoRotate}
      />

      {/* ── HUD overlays ──────────────────────── */}
      <HUD
        pointData={pointData}
        loading={loading}
        error={error}
        stats={stats}
        colorMode={colorMode}
        onColorModeChange={setColorMode}
        autoRotate={autoRotate}
        onAutoRotateToggle={() => setAutoRotate((v) => !v)}
      />
    </div>
  );
}
