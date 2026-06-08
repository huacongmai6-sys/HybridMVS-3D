/**
 * Pure ASCII PLY parser.
 * Extracted from Viewer3D for reuse across the app.
 *
 * @param {string} text - PLY file contents as string
 * @returns {{ positions: Float32Array, colors: Float32Array, count: number, center: [number,number,number], extent: number, bbox: {xmin,ymin,zmin,xmax,ymax,zmax} }}
 */
export function parsePLY(text) {
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
      if (isNaN(x) || isNaN(y) || isNaN(z)) continue;

      positions.push(x, y, z);
      cx += x; cy += y; cz += z;
      if (x < xmin) xmin = x; if (x > xmax) xmax = x;
      if (y < ymin) ymin = y; if (y > ymax) ymax = y;
      if (z < zmin) zmin = z; if (z > zmax) zmax = z;

      if (parts.length >= 6) {
        colors.push(
          parseInt(parts[3]) / 255,
          parseInt(parts[4]) / 255,
          parseInt(parts[5]) / 255
        );
      } else {
        // Default blue-ish
        colors.push(0.45, 0.62, 0.91);
      }
      count++;
    }
  }

  if (count === 0) {
    return { positions: new Float32Array(), colors: new Float32Array(), count: 0, center: [0, 0, 0], extent: 1, bbox: { xmin: 0, ymin: 0, zmin: 0, xmax: 0, ymax: 0, zmax: 0 } };
  }

  cx /= count; cy /= count; cz /= count;
  const extent = Math.max(xmax - xmin, ymax - ymin, zmax - zmin, 1);

  return {
    positions: new Float32Array(positions),
    colors: new Float32Array(colors),
    count,
    center: [cx, cy, cz],
    extent,
    bbox: { xmin, ymin, zmin, xmax, ymax, zmax },
  };
}
