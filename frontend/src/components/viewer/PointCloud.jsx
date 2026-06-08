import { useRef, useMemo } from "react";
import * as THREE from "three";
import { computeDepthColors } from "../../utils/colorMapping";

/**
 * PointCloud — Renders a BufferGeometry-based point cloud.
 *
 * @param {{ pointData: { positions, colors, count, center, extent } | null,
 *            colorMode: "rgb" | "depth" | "confidence" }} props
 */
export default function PointCloud({ pointData, colorMode = "rgb" }) {
  const ref = useRef();

  /* Build geometry and colors based on colorMode */
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
    const mat = new THREE.PointsMaterial({
      size: pointSize,
      vertexColors: true,
      sizeAttenuation: true,
      blending: THREE.NormalBlending,
      depthWrite: true,
    });

    return { geo, mat };
  }, [pointData, colorMode]);

  if (!geo) return null;

  return <points ref={ref} geometry={geo} material={mat} />;
}
