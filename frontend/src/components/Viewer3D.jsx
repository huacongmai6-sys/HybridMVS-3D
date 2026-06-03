import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

function Scene({ pointData, autoRotate, orbitRef }) {
  const pointsRef = useRef();

  // Auto-rotation via OrbitControls ref
  useEffect(() => {
    if (orbitRef?.current) {
      orbitRef.current.autoRotate = autoRotate;
      orbitRef.current.autoRotateSpeed = 0.6;
    }
  }, [autoRotate, orbitRef]);

  if (!pointData) return null;

  return (
    <>
      <ambientLight intensity={0.45} />
      <directionalLight position={[8, 15, 8]} intensity={0.6} />
      <directionalLight position={[-5, -3, -5]} intensity={0.2} />
      <OrbitControls
        ref={orbitRef}
        target={pointData.center}
        enableDamping
        dampingFactor={0.08}
        enablePan
        enableZoom
        enableRotate
        rotateSpeed={0.8}
        panSpeed={0.8}
        zoomSpeed={1.0}
        minPolarAngle={0}
        maxPolarAngle={Math.PI}
        minAzimuthAngle={-Infinity}
        maxAzimuthAngle={Infinity}
        minDistance={pointData.extent * 0.02}
        maxDistance={pointData.extent * 15}
      />
      <points ref={pointsRef}>
        <bufferGeometry attach="geometry" {...pointData.geo} />
        <pointsMaterial
          attach="material"
          size={pointData.pointSize}
          vertexColors
          sizeAttenuation
          blending={THREE.NormalBlending}
          depthWrite
        />
      </points>
    </>
  );
}

export default function Viewer3D({ modelUrl }) {
  const [pointData, setPointData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [autoRotate, setAutoRotate] = useState(false);
  const orbitRef = useRef();

  // Load and parse PLY outside of Canvas
  useEffect(() => {
    if (!modelUrl) return;
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
        const lines = text.split("\n");
        const positions = [];
        const colors = [];
        let inHeader = true;
        let cx = 0, cy = 0, cz = 0;
        let count = 0;
        let xmin = Infinity, ymin = Infinity, zmin = Infinity;
        let xmax = -Infinity, ymax = -Infinity, zmax = -Infinity;

        for (const line of lines) {
          if (inHeader) {
            if (line.trim() === "end_header") inHeader = false;
            continue;
          }
          if (!line.trim()) continue;
          const parts = line.trim().split(/\s+/);
          if (parts.length >= 3) {
            const x = parseFloat(parts[0]);
            const y = parseFloat(parts[1]);
            const z = parseFloat(parts[2]);
            positions.push(x, y, z);
            cx += x; cy += y; cz += z;
            if (x < xmin) xmin = x; if (x > xmax) xmax = x;
            if (y < ymin) ymin = y; if (y > ymax) ymax = y;
            if (z < zmin) zmin = z; if (z > zmax) zmax = z;
            if (parts.length >= 6) {
              colors.push(
                parseInt(parts[3]) / 255,
                parseInt(parts[4]) / 255,
                parseInt(parts[5]) / 255,
              );
            } else {
              colors.push(0.45, 0.62, 0.91);
            }
            count++;
          }
        }

        if (count > 0) {
          cx /= count; cy /= count; cz /= count;
          const extent = Math.max(xmax - xmin, ymax - ymin, zmax - zmin, 1);
          const geo = new THREE.BufferGeometry();
          geo.setAttribute(
            "position",
            new THREE.Float32BufferAttribute(positions, 3),
          );
          geo.setAttribute(
            "color",
            new THREE.Float32BufferAttribute(colors, 3),
          );
          const pointSize = extent * 0.004;
          if (active)
            setPointData({ geo, count, center: [cx, cy, cz], extent, pointSize });
        } else if (active) {
          setError("点云为空 — 没有读取到有效顶点数据");
        }
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [modelUrl]);

  // ── Placeholder state ────────────────────────────────
  if (!modelUrl) {
    return (
      <div className="viewer-placeholder">
        <div className="placeholder-icon">◈</div>
        <p>上传图片或视频并开始重建<br />三维模型将在此处显示</p>
        <span className="hint-text">
          支持 PLY 稠密点云 · 旋转 / 缩放 / 平移
        </span>
      </div>
    );
  }

  const canvasBg = "#0b1019";

  return (
    <div className="viewer-3d" style={{ position: "relative" }}>
      {/* ── Top HUD: status badge ───────────────────── */}
      <div className="viewer-hud viewer-hud-top">
        {loading && (
          <div className="viewer-hud-badge">
            <span className="dot" />
            加载点云数据...
          </div>
        )}
        {error && (
          <div className="viewer-hud-badge error">
            <span className="dot" />
            加载失败: {error}
          </div>
        )}
        {pointData && !loading && (
          <div className="viewer-hud-badge">
            <span className="dot" />
            模型已就绪
          </div>
        )}
      </div>

      {/* ── Bottom HUD: stats + controls ────────────── */}
      {pointData && !loading && !error && (
        <div className="viewer-hud viewer-hud-bottom">
          <div className="viewer-stats">
            <div className="viewer-stat">
              顶点
              <span className="stat-value">
                {(pointData.count / 1000).toFixed(0)}K
              </span>
            </div>
            <span className="stat-divider">|</span>
            <div className="viewer-stat">
              范围
              <span className="stat-value">
                {pointData.extent.toFixed(2)}
              </span>
            </div>
            <span className="stat-divider">|</span>
            <button
              className={`btn-auto-rotate ${autoRotate ? "active" : ""}`}
              onClick={() => setAutoRotate((v) => !v)}
              title={autoRotate ? "停止旋转" : "自动旋转"}
              style={{
                background: "none",
                border: "none",
                color: autoRotate ? "var(--accent)" : "var(--text-muted)",
                cursor: "pointer",
                fontSize: 13,
                fontFamily: "var(--font-body)",
                pointerEvents: "auto",
                padding: "0 4px",
                transition: "color 0.2s",
              }}
            >
              {autoRotate ? "⟳ 旋转中" : "↻ 旋转"}
            </button>
          </div>
        </div>
      )}

      <Canvas
        camera={{
          position: pointData
            ? [
                pointData.center[0] + pointData.extent * 1.4,
                pointData.center[1] + pointData.extent * 0.8,
                pointData.center[2] + pointData.extent * 1.4,
              ]
            : [3, 3, 3],
          up: [0, -1, 0],
          fov: 50,
        }}
        gl={{ antialias: true, alpha: false }}
        style={{ background: canvasBg, cursor: "grab" }}
      >
        <Scene pointData={pointData} autoRotate={autoRotate} orbitRef={orbitRef} />
      </Canvas>
    </div>
  );
}
