/**
 * Color mapping utilities for point cloud display modes.
 *
 * depthColor(value, min, max)  → [r, g, b]  (jet colormap: blue→cyan→green→yellow→red)
 * confidenceColor(value)       → [r, g, b]  (gray→green gradient)
 */

/**
 * Jet colormap — maps a normalized value (0–1) to an RGB triplet.
 * Blue (far/cold) → Cyan → Green → Yellow → Red (near/hot)
 */
function jet(t) {
  /* Clamp */
  if (t < 0) t = 0;
  if (t > 1) t = 1;

  const r = Math.min(Math.max(1.5 - Math.abs(4 * t - 3), 0), 1);
  const g = Math.min(Math.max(1.5 - Math.abs(4 * t - 2), 0), 1);
  const b = Math.min(Math.max(1.5 - Math.abs(4 * t - 1), 0), 1);
  return [r, g, b];
}

/**
 * Map a depth value to an RGB color using the jet colormap.
 * @param {number} value - depth value (e.g., distance from centroid)
 * @param {number} minVal - minimum depth in the dataset
 * @param {number} maxVal - maximum depth in the dataset
 * @returns {[number, number, number]} RGB values (0–1)
 */
export function depthColor(value, minVal, maxVal) {
  const range = maxVal - minVal || 1;
  const t = (value - minVal) / range;
  return jet(t);
}

/**
 * Pre-compute depth colors for an entire point cloud.
 * Returns a Float32Array of RGB values that can be assigned to a BufferAttribute.
 *
 * @param {Float32Array} positions - flat positions array [x1,y1,z1, x2,y2,z2, ...]
 * @param {number} count - number of points
 * @param {[number,number,number]} center - [cx, cy, cz] centroid for distance calculation
 * @returns {Float32Array} flat colors array [r1,g1,b1, r2,g2,b2, ...]
 */
export function computeDepthColors(positions, count, center) {
  const colors = new Float32Array(count * 3);

  /* First pass: compute distances and find min/max */
  let minDist = Infinity, maxDist = -Infinity;
  const dists = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    const dx = positions[i * 3] - center[0];
    const dy = positions[i * 3 + 1] - center[1];
    const dz = positions[i * 3 + 2] - center[2];
    const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
    dists[i] = d;
    if (d < minDist) minDist = d;
    if (d > maxDist) maxDist = d;
  }

  /* Second pass: map to colors */
  for (let i = 0; i < count; i++) {
    const [r, g, b] = depthColor(dists[i], minDist, maxDist);
    colors[i * 3] = r;
    colors[i * 3 + 1] = g;
    colors[i * 3 + 2] = b;
  }

  return colors;
}

/**
 * Confidence color mapping — gray (low) → green (high).
 * @param {number} value - confidence value (0–1)
 * @returns {[number, number, number]} RGB values (0–1)
 */
export function confidenceColor(value) {
  if (value == null) return [0.3, 0.3, 0.3];
  const t = Math.min(Math.max(value, 0), 1);
  return [
    0.2 + t * 0.1,      // R: 0.2 → 0.3
    0.3 + t * 0.7,      // G: 0.3 → 1.0
    0.2 + t * 0.1,      // B: 0.2 → 0.3
  ];
}

// ── Distance Error Colormap (for comparison overlay) ─────

/**
 * Green → Yellow → Red colormap for distance error visualization.
 * Green  (t=0.0): very close match
 * Yellow (t=0.5): moderate error
 * Red    (t=1.0): large error
 *
 * @param {number} t - normalized value [0, 1]
 * @returns {[number, number, number]} RGB values (0–1)
 */
export function distanceColor(t) {
  if (t < 0) t = 0;
  if (t > 1) t = 1;

  if (t < 0.5) {
    // Green (0,1,0) → Yellow (1,1,0)
    const s = t / 0.5;
    return [s, 1.0, 0.0];
  } else {
    // Yellow (1,1,0) → Red (1,0,0)
    const s = (t - 0.5) / 0.5;
    return [1.0, 1.0 - s, 0.0];
  }
}

/**
 * Pre-compute comparison heatmap colors from per-point distances.
 *
 * @param {Float32Array} distances - per-point distance values
 * @param {number} count - number of points
 * @param {number} [maxDist] - distance that maps to red (default: computed from data)
 * @returns {Float32Array} flat colors array [r1,g1,b1, r2,g2,b2, ...]
 */
export function computeComparisonColors(distances, count, maxDist = null) {
  const colors = new Float32Array(count * 3);
  let minD = Infinity;
  let maxD = -Infinity;
  for (let i = 0; i < count; i++) {
    const d = distances[i];
    if (d < minD) minD = d;
    if (d > maxD) maxD = d;
  }
  const range = (maxDist != null ? maxDist : maxD) - minD || 1;
  for (let i = 0; i < count; i++) {
    const t = (distances[i] - minD) / range;
    const [r, g, b] = distanceColor(t);
    colors[i * 3] = r;
    colors[i * 3 + 1] = g;
    colors[i * 3 + 2] = b;
  }
  return colors;
}
