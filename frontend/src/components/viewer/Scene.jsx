import { useRef, useEffect } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Grid } from "@react-three/drei";
import PointCloud from "./PointCloud";

/**
 * CameraSync — keeps camera in sync with point cloud center/extent.
 */
function CameraSetup({ center, extent }) {
  const { camera } = useThree();

  useEffect(() => {
    if (!center || !extent) return;
    camera.position.set(
      center[0] + extent * 1.4,
      center[1] + extent * 0.8,
      center[2] + extent * 1.4
    );
    camera.lookAt(center[0], center[1], center[2]);
  }, [center, extent, camera]);

  return null;
}

/**
 * SceneInner — renders inside the R3F Canvas.
 */
function SceneInner({
  pointData,
  colorMode,
  orbitRef,
  autoRotate,
}) {
  return (
    <>
      {/* ── Lighting ──────────────────────────── */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[8, 15, 8]} intensity={0.55} />
      <directionalLight position={[-5, -3, -5]} intensity={0.15} />

      {/* ── Orbit Controls ────────────────────── */}
      {pointData && (
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
          minDistance={pointData.extent * 0.02}
          maxDistance={pointData.extent * 15}
        />
      )}

      {/* ── Ground Grid ───────────────────────── */}
      {pointData && (
        <Grid
          position={[pointData.center[0], pointData.center[1] - pointData.extent * 0.5, pointData.center[2]]}
          cellSize={pointData.extent * 0.1}
          cellThickness={0.5}
          cellColor="#243044"
          sectionSize={pointData.extent * 0.5}
          sectionThickness={1.5}
          sectionColor="#1A2332"
          fadeDistance={pointData.extent * 3}
          infiniteGrid
        />
      )}

      {/* ── Point Cloud ───────────────────────── */}
      <PointCloud pointData={pointData} colorMode={colorMode} />

      {/* ── Camera ─────────────────────────────── */}
      {pointData && (
        <CameraSetup center={pointData.center} extent={pointData.extent} />
      )}
    </>
  );
}

/**
 * Scene — R3F Canvas wrapper.
 */
export default function Scene({ pointData, colorMode, orbitRef, autoRotate }) {
  return (
    <Canvas
      camera={{
        fov: 50,
        near: 0.001,
        far: 1000,
      }}
      up={[0, -1, 0]}
      gl={{ antialias: true, alpha: false }}
      style={{ background: "#0B1020", cursor: pointData ? "grab" : "default" }}
    >
      <SceneInner
        pointData={pointData}
        colorMode={colorMode}
        orbitRef={orbitRef}
        autoRotate={autoRotate}
      />
    </Canvas>
  );
}
