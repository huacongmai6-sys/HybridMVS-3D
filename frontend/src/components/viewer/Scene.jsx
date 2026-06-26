import { useEffect, useRef } from "react";
import { Canvas, useThree, useFrame } from "@react-three/fiber";
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
 *
 * Tracks mouse NDC from R3F's internal pointer state and passes
 * it as a ref to the PointCloud shader for the mouse-reveal spotlight.
 */
function SceneInner({
  pointData,
  colorMode,
  orbitRef,
  autoRotate,
}) {
  /* Mouse NDC tracking via R3F's internal pointer state */
  const mouseRef = useRef({ x: -99, y: -99 });

  useFrame((state) => {
    mouseRef.current.x = state.pointer.x;
    mouseRef.current.y = state.pointer.y;
  });

  return (
    <>
      {/* ── Ultra-subtle ambient (ShaderMaterial ignores, kept for any future lit meshes) ── */}
      <ambientLight intensity={0.1} />

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

      {/* ── Ultra-subtle grid — barely visible on pure black ── */}
      {pointData && (
        <Grid
          position={[
            pointData.center[0],
            pointData.center[1] - pointData.extent * 0.5,
            pointData.center[2],
          ]}
          cellSize={pointData.extent * 0.1}
          cellThickness={0.3}
          cellColor="#0a0d12"
          sectionSize={pointData.extent * 0.5}
          sectionThickness={0.8}
          sectionColor="#0f131a"
          fadeDistance={pointData.extent * 3}
          infiniteGrid
        />
      )}

      {/* ── Point Cloud with wave-reveal shader ── */}
      <PointCloud
        pointData={pointData}
        colorMode={colorMode}
        mouseRef={mouseRef}
      />

      {/* ── Camera sync ────────────────────────── */}
      {pointData && (
        <CameraSetup center={pointData.center} extent={pointData.extent} />
      )}
    </>
  );
}

/**
 * Scene — R3F Canvas wrapper.
 */
export default function Scene({
  pointData,
  colorMode,
  orbitRef,
  autoRotate,
}) {
  return (
    <Canvas
      camera={{
        fov: 50,
        near: 0.001,
        far: 1000,
      }}
      up={[0, -1, 0]}
      gl={{ antialias: true, alpha: false }}
      style={{ background: "#000000", cursor: pointData ? "grab" : "default" }}
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
