import { useState, useEffect, useRef, useCallback } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Grid } from "@react-three/drei";
import * as THREE from "three";
import { parsePLY } from "../../utils/plyParser";
import { distanceColor } from "../../utils/colorMapping";

// ── CameraSetup ──────────────────────────────────────────────
function CameraSetup({ center, extent }) {
  const { camera } = useThree();
  useEffect(() => {
    if (!center || !extent) return;
    camera.position.set(
      center[0] + extent * 1.4,
      center[1] + extent * 0.8,
      center[2] + extent * 1.4,
    );
    camera.lookAt(center[0], center[1], center[2]);
  }, [center, extent, camera]);
  return null;
}

// ── Single point cloud renderer ──────────────────────────────
function PointsMesh({ pointData, uniformColor, opacity }) {
  const geoRef = useRef(null);

  if (!pointData || pointData.count === 0) return null;

  let colors;
  if (uniformColor) {
    colors = new Float32Array(pointData.count * 3);
    for (let i = 0; i < pointData.count; i++) {
      colors[i * 3] = uniformColor[0];
      colors[i * 3 + 1] = uniformColor[1];
      colors[i * 3 + 2] = uniformColor[2];
    }
  } else {
    colors = pointData.colors;
  }

  return (
    <points>
      <bufferGeometry ref={geoRef}>
        <bufferAttribute
          attach="attributes-position"
          count={pointData.count}
          array={pointData.positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={pointData.count}
          array={colors}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={pointData.extent * 0.005}
        vertexColors
        sizeAttenuation
        transparent={opacity !== undefined}
        opacity={opacity}
        depthWrite={opacity === 1.0 || opacity === undefined}
        blending={THREE.NormalBlending}
      />
    </points>
  );
}

// ── Scene Inner ──────────────────────────────────────────────
function SceneInner({
  gtData,
  colmapData,
  mvsData,
  showGT,
  showColmap,
  showMVS,
  orbitRef,
  colorMode, // "identity" | "heatmap"
}) {
  const center = gtData?.center || colmapData?.center || mvsData?.center || [0, 0, 0];
  const extent =
    gtData?.extent || colmapData?.extent || mvsData?.extent || 1;

  return (
    <>
      <ambientLight intensity={0.45} />
      <directionalLight position={[8, 15, 8]} intensity={0.55} />
      <directionalLight position={[-5, -3, -5]} intensity={0.15} />

      <OrbitControls
        ref={orbitRef}
        target={center}
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
        minDistance={extent * 0.02}
        maxDistance={extent * 15}
      />

      <Grid
        position={[center[0], center[1] - extent * 0.5, center[2]]}
        cellSize={extent * 0.1}
        cellThickness={0.5}
        cellColor="#243044"
        sectionSize={extent * 0.5}
        sectionThickness={1.5}
        sectionColor="#1A2332"
        fadeDistance={extent * 3}
        infiniteGrid
      />

      <CameraSetup center={center} extent={extent} />

      {showGT && gtData && (
        <PointsMesh
          pointData={gtData}
          uniformColor={colorMode === "heatmap" ? null : [0.85, 0.85, 0.88]}
          opacity={0.55}
        />
      )}
      {showColmap && colmapData && (
        <PointsMesh
          pointData={colmapData}
          uniformColor={colorMode === "heatmap" ? null : [0.31, 0.56, 1.0]}
        />
      )}
      {showMVS && mvsData && (
        <PointsMesh
          pointData={mvsData}
          uniformColor={colorMode === "heatmap" ? null : [1.0, 0.55, 0.2]}
        />
      )}
    </>
  );
}

// ── Legend Bar ───────────────────────────────────────────────
function LegendBar({ visible }) {
  if (!visible) return null;
  const steps = 100;
  const bars = [];
  for (let i = 0; i < steps; i++) {
    const t = i / (steps - 1);
    const [r, g, b] = distanceColor(t);
    bars.push(
      <div
        key={i}
        style={{
          flex: 1,
          backgroundColor: `rgb(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)})`,
          height: "100%",
        }}
      />,
    );
  }

  return (
    <div className="comparison-legend">
      <span className="legend-label">0mm (close)</span>
      <div className="legend-gradient">{bars}</div>
      <span className="legend-label">max (far)</span>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────
/**
 * ComparisonViewer — 3-way point cloud overlay in a single 3D scene.
 *
 * Props:
 *   gtUrl, colmapUrl, mvsUrl       — PLY download URLs
 *   gtColoredUrl, colmapColoredUrl, mvsColoredUrl — heatmap PLY URLs
 *   metrics                         — comparison result object
 */
export default function ComparisonViewer({
  gtUrl,
  colmapUrl,
  mvsUrl,
  gtColoredUrl,
  colmapColoredUrl,
  mvsColoredUrl,
  metrics,
}) {
  const [gtData, setGtData] = useState(null);
  const [colmapData, setColmapData] = useState(null);
  const [mvsData, setMvsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showGT, setShowGT] = useState(true);
  const [showColmap, setShowColmap] = useState(true);
  const [showMVS, setShowMVS] = useState(true);
  const [colorMode, setColorMode] = useState("identity"); // "identity" | "heatmap"
  const orbitRef = useRef(null);

  // ── Load PLYs ────────────────────────────────────────────
  useEffect(() => {
    if (!gtUrl && !colmapUrl && !mvsUrl) return;

    let active = true;
    setLoading(true);
    setError(null);

    const loadAll = async () => {
      const results = {};
      const urls = { gt: gtUrl, colmap: colmapUrl, mvs: mvsUrl };
      const coloredUrls = {
        gt: gtColoredUrl,
        colmap: colmapColoredUrl,
        mvs: mvsColoredUrl,
      };

      // Load base PLYs
      for (const [key, url] of Object.entries(urls)) {
        if (!url) continue;
        try {
          const res = await fetch(url);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const text = await res.text();
          results[key] = parsePLY(text);
        } catch (e) {
          console.warn(`Failed to load ${key} PLY:`, e.message);
        }
      }

      if (!active) return;

      // Load colored PLYs (for heatmap mode — parse colors from vertex data)
      const coloredParsed = {};
      for (const [key, url] of Object.entries(coloredUrls)) {
        if (!url || !results[key]) continue;
        try {
          const res = await fetch(url);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const text = await res.text();
          coloredParsed[key] = parsePLY(text);
        } catch (e) {
          console.warn(`Failed to load ${key} colored PLY:`, e.message);
        }
      }

      if (!active) return;

      // Store both versions: base (identity colors) and heatmap (distance colors)
      setGtData({
        identity: results.gt || null,
        heatmap: coloredParsed.gt || null,
      });
      setColmapData({
        identity: results.colmap || null,
        heatmap: coloredParsed.colmap || null,
      });
      setMvsData({
        identity: results.mvs || null,
        heatmap: coloredParsed.mvs || null,
      });

      // Auto-set center from first available data
      setLoading(false);
    };

    loadAll().catch((err) => {
      if (active) {
        console.error(err);
        setError(err.message);
        setLoading(false);
      }
    });

    return () => {
      active = false;
    };
  }, [gtUrl, colmapUrl, mvsUrl, gtColoredUrl, colmapColoredUrl, mvsColoredUrl]);

  // ── Get active data based on color mode ────────────────────
  const getActive = (data) => {
    if (!data) return null;
    return colorMode === "heatmap" ? data.heatmap : data.identity;
  };

  const hasData = gtData || colmapData || mvsData;

  // ── Loading / Empty states ────────────────────────────────
  if (!gtUrl && !colmapUrl && !mvsUrl) {
    return (
      <div className="viewer-placeholder">
        <div className="placeholder-icon">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"
               strokeLinejoin="round">
            <circle cx="5" cy="5" r="3"/><circle cx="19" cy="5" r="3"/>
            <circle cx="12" cy="19" r="3"/>
            <line x1="8" y1="5" x2="5.5" y2="16"/>
            <line x1="16" y1="5" x2="17" y2="16"/>
            <line x1="12" y1="5" x2="12" y2="16"/>
          </svg>
        </div>
        <p>上传点云并运行对比<br />3D 可视化将在此处显示</p>
        <span className="placeholder-hint">GT · COLMAP · MVS — 三方叠加对比</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="viewer-placeholder">
        <div className="loading-spinner" />
        <p>加载点云数据…</p>
      </div>
    );
  }

  if (error && !hasData) {
    return (
      <div className="viewer-placeholder">
        <div className="placeholder-icon error-icon">!</div>
        <p className="error-text">{error}</p>
      </div>
    );
  }

  return (
    <div className="viewer-3d comparison-viewer-3d">
      {/* ── Toggle bar ─────────────────────────── */}
      <div className="comparison-toggles">
        <button
          className={`toggle-btn ${showGT ? "active gt" : ""}`}
          onClick={() => setShowGT((v) => !v)}
          title="Ground Truth"
        >
          <span className="toggle-dot gt-dot" /> GT
        </button>
        <button
          className={`toggle-btn ${showColmap ? "active colmap" : ""}`}
          onClick={() => setShowColmap((v) => !v)}
          title="COLMAP Dense"
        >
          <span className="toggle-dot colmap-dot" /> COLMAP
        </button>
        <button
          className={`toggle-btn ${showMVS ? "active mvs" : ""}`}
          onClick={() => setShowMVS((v) => !v)}
          title="MVS Network"
        >
          <span className="toggle-dot mvs-dot" /> MVS
        </button>
        <div className="toggle-separator" />
        <button
          className={`toggle-btn mode ${colorMode === "identity" ? "active" : ""}`}
          onClick={() => setColorMode("identity")}
          title="Each point cloud in its own colour"
        >
          分类色
        </button>
        <button
          className={`toggle-btn mode ${colorMode === "heatmap" ? "active" : ""}`}
          onClick={() => setColorMode("heatmap")}
          title="Coloured by distance error"
        >
          距离热力图
        </button>
      </div>

      {/* ── Legend ──────────────────────────────── */}
      <LegendBar visible={colorMode === "heatmap"} />

      {/* ── Canvas ───────────────────────────────── */}
      <Canvas
        camera={{ fov: 50, near: 0.001, far: 1000 }}
        up={[0, -1, 0]}
        gl={{ antialias: true, alpha: false }}
        style={{ background: "#0B1020" }}
      >
        <SceneInner
          gtData={getActive(gtData)}
          colmapData={getActive(colmapData)}
          mvsData={getActive(mvsData)}
          showGT={showGT}
          showColmap={showColmap}
          showMVS={showMVS}
          orbitRef={orbitRef}
          colorMode={colorMode}
        />
      </Canvas>

      {/* ── Loading overlay ───────────────────────── */}
      {loading && (
        <div className="viewer-loading-overlay">
          <div className="loading-spinner" />
        </div>
      )}
    </div>
  );
}
