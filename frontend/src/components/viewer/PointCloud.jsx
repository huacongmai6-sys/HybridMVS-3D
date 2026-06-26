import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { computeDepthColors } from "../../utils/colorMapping";
import { createWaveMaterial } from "./WaveShader";

/**
 * PointCloud — Renders the point cloud with a wave-reveal shader.
 *
 * Points are hidden by default and revealed by:
 *   1. Breathing concentric rings expanding from top-center (primary)
 *   2. Mouse cursor spotlight (supplemental)
 *
 * @param {{ pointData: { positions, colors, count, center, extent } | null,
 *            colorMode: "rgb" | "depth" | "confidence",
 *            mouseRef: React.RefObject<{{ x: number, y: number }}> }} props
 */
export default function PointCloud({ pointData, colorMode = "rgb", mouseRef }) {
  const ref = useRef();

  /* Build geometry once per pointData/colorMode change */
  const { geo, mat } = useMemo(() => {
    if (!pointData || pointData.count === 0) return { geo: null, mat: null };

    const geo = new THREE.BufferGeometry();

    /* Position attribute */
    geo.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(pointData.positions, 3)
    );

    /* Color attribute — depends on mode */
    let colorArr;
    if (colorMode === "depth") {
      colorArr = computeDepthColors(
        pointData.positions,
        pointData.count,
        pointData.center
      );
    } else if (colorMode === "confidence") {
      /* Placeholder: gray uniform color */
      colorArr = new Float32Array(pointData.count * 3);
      for (let i = 0; i < pointData.count; i++) {
        colorArr[i * 3] = 0.35;
        colorArr[i * 3 + 1] = 0.4;
        colorArr[i * 3 + 2] = 0.45;
      }
    } else {
      /* RGB mode — use parsed colors */
      colorArr = pointData.colors;
    }

    geo.setAttribute("color", new THREE.Float32BufferAttribute(colorArr, 3));

    const pointSize = pointData.extent * 0.004;
    const mat = createWaveMaterial(pointSize, pointData.extent);

    return { geo, mat };
  }, [pointData, colorMode]);

  /* Per-frame uniform updates */
  useFrame(({ clock, size: viewport, gl: renderer }) => {
    if (!mat) return;

    // Elapsed time — drives the breathing wave animation
    mat.uniforms.uTime.value = clock.getElapsedTime();

    // Viewport resolution (for aspect-corrected distance calculations)
    const dpr = renderer.getPixelRatio();
    mat.uniforms.uResolution.value.set(
      viewport.width * dpr,
      viewport.height * dpr
    );

    // Size attenuation scale (matches THREE.PointsMaterial behavior)
    mat.uniforms.uScale.value = viewport.height * dpr * 0.5;

    // Mouse NDC position
    if (mouseRef?.current) {
      mat.uniforms.uMouse.value.set(
        mouseRef.current.x,
        mouseRef.current.y
      );
    }
  });

  if (!geo) return null;

  return <points ref={ref} geometry={geo} material={mat} />;
}
