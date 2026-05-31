/** API client for HybridMVS backend. */
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

export async function uploadImages(files, quality = "high") {
  const form = new FormData();
  files.forEach((f) => form.append("images", f));
  form.append("quality", quality);

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

export async function healthCheck() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
