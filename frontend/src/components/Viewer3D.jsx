import { useState, useEffect, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";

export default function Viewer3D({ modelUrl }) {
  const [pointData, setPointData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

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
              colors.push(parseInt(parts[3]) / 255, parseInt(parts[4]) / 255, parseInt(parts[5]) / 255);
            } else {
              colors.push(0.6, 0.6, 0.7);
            }
            count++;
          }
        }

        if (count > 0) {
          cx /= count; cy /= count; cz /= count;
          const extent = Math.max(xmax - xmin, ymax - ymin, zmax - zmin, 1);
          const geo = new THREE.BufferGeometry();
          geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
          geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
          const pointSize = extent * 0.005;
          if (active) setPointData({ geo, count, center: [cx, cy, cz], extent, pointSize });
        } else if (active) {
          setError("点云为空");
        }
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [modelUrl]);

  if (!modelUrl) {
    return (
      <div className="viewer-placeholder">
        <p>上传图片并开始重建后，三维模型将在此处显示</p>
      </div>
    );
  }

  return (
    <div className="viewer-3d" style={{ position: "relative" }}>
      {loading && (
        <div style={{ position: "absolute", top: 16, left: "50%", zIndex: 10,
          transform: "translateX(-50%)", background: "rgba(0,0,0,0.8)",
          color: "#58a6ff", padding: "8px 20px", borderRadius: 8, fontSize: 14 }}>
          加载中...
        </div>
      )}
      {error && (
        <div style={{ position: "absolute", top: 16, left: "50%", zIndex: 10,
          transform: "translateX(-50%)", background: "rgba(248,81,73,0.2)",
          color: "#f85149", padding: "8px 20px", borderRadius: 8, fontSize: 14 }}>
          加载失败: {error}
        </div>
      )}
      {pointData && !loading && (
        <div style={{ position: "absolute", bottom: 16, left: "50%", zIndex: 10,
          transform: "translateX(-50%)", background: "rgba(0,0,0,0.7)",
          color: "#8b949e", padding: "4px 16px", borderRadius: 6, fontSize: 12 }}>
          {pointData.count.toLocaleString()} 个点 | 范围 {pointData.extent.toFixed(1)}
        </div>
      )}
      <Canvas
        camera={{ position: pointData
          ? [pointData.center[0] + pointData.extent * 1.5,
             pointData.center[1] + pointData.extent * 1.5,
             pointData.center[2] + pointData.extent * 1.5]
          : [3, 3, 3],
          up: [0, -1, 0],  // flip Y-axis: COLMAP Y-up → screen Y-down
          fov: 50 }}
        gl={{ antialias: true }}
        style={{ background: "#1a1a2e", cursor: "grab" }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={0.8} />
        <OrbitControls
          target={pointData ? pointData.center : [0, 0, 0]}
          enableDamping
          dampingFactor={0.1}
          enablePan
          enableZoom
          enableRotate
          rotateSpeed={1.0}
          panSpeed={1.0}
          zoomSpeed={1.0}
          minPolarAngle={0}
          maxPolarAngle={Math.PI}
          minAzimuthAngle={-Infinity}
          maxAzimuthAngle={Infinity}
          minDistance={pointData ? pointData.extent * 0.02 : 0.02}
          maxDistance={pointData ? pointData.extent * 20 : 100}
        />
        {pointData && (
          <points>
            <bufferGeometry attach="geometry" {...pointData.geo} />
            <pointsMaterial
              attach="material"
              size={pointData.pointSize}
              vertexColors
              sizeAttenuation
            />
          </points>
        )}
      </Canvas>
    </div>
  );
}
