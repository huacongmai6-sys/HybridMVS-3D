/** API client for HybridMVS backend. */
const API_BASE = import.meta.env.VITE_API_URL || "";

export async function uploadImages(files, quality = "high", mode = "colmap") {
  const form = new FormData();
  files.forEach((f) => form.append("images", f));
  form.append("input_type", "images");
  form.append("quality", quality);
  form.append("mode", mode);

  const res = await fetch(`${API_BASE}/api/tasks`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function uploadVideo(file, quality = "high", mode = "colmap", targetFrames = 30) {
  const form = new FormData();
  form.append("video", file);
  form.append("input_type", "video");
  form.append("quality", quality);
  form.append("mode", mode);
  form.append("target_frames", String(targetFrames));

  const res = await fetch(`${API_BASE}/api/tasks`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function getTask(taskId) {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}`);
  if (!res.ok) throw new Error(`Fetch failed: ${res.statusText}`);
  return res.json();
}

export async function listTasks() {
  const res = await fetch(`${API_BASE}/api/tasks`);
  if (!res.ok) throw new Error(`List failed: ${res.statusText}`);
  return res.json();
}

export async function deleteTask(taskId) {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete failed: ${res.statusText}`);
  return res.json();
}

export async function runTaskSync(taskId) {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}/run`, { method: "POST" });
  if (!res.ok) throw new Error(`Run failed: ${res.statusText}`);
  return res.json();
}

export function getDownloadUrl(taskId, filetype) {
  return `${API_BASE}/api/tasks/${taskId}/download/${filetype}`;
}

export function getDepthPreviewUrl(taskId, filename) {
  return `${API_BASE}/api/tasks/${taskId}/depth_previews/${filename}`;
}

// ── Point Cloud Comparison ───────────────────────────

export async function uploadComparison(gtFile, colmapFile, mvsFile, align = false, estimateNormal = true) {
  const form = new FormData();
  form.append("gt_file", gtFile);
  form.append("colmap_file", colmapFile);
  form.append("mvs_file", mvsFile);
  form.append("align", String(align));
  form.append("estimate_normal", String(estimateNormal));

  const res = await fetch(`${API_BASE}/api/compare`, { method: "POST", body: form });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `Comparison failed: ${res.statusText}`);
  }
  return res.json();
}

export async function getComparison(comparisonId) {
  const res = await fetch(`${API_BASE}/api/compare/${comparisonId}`);
  if (!res.ok) throw new Error(`Fetch comparison failed: ${res.statusText}`);
  return res.json();
}

export function getComparisonDownloadUrl(comparisonId, filetype) {
  return `${API_BASE}/api/compare/${comparisonId}/download/${filetype}`;
}

export async function healthCheck() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
