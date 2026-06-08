/**
 * Formatting utilities for display values.
 */

/**
 * Format a number with compact notation.
 * @param {number} n
 * @returns {string} e.g. "1.2K", "3.4M", "662K"
 */
export function formatCount(n) {
  if (n == null) return "—";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

/**
 * Format seconds to a human-readable duration.
 * @param {number} seconds
 * @returns {string} e.g. "2m 34s", "1h 5m", "45s"
 */
export function formatDuration(seconds) {
  if (seconds == null || isNaN(seconds)) return "—";
  if (seconds < 60) return Math.round(seconds) + "s";
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
  }
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

/**
 * Format a decimal as a percentage string.
 * @param {number} n - value between 0 and 1
 * @returns {string} e.g. "88.2%"
 */
export function formatPercent(n) {
  if (n == null) return "—";
  return (n * 100).toFixed(1) + "%";
}

/**
 * Format depth in meters.
 * @param {number} v
 * @returns {string} e.g. "3.42m"
 */
export function formatDepth(v) {
  if (v == null) return "—";
  return v.toFixed(2) + "m";
}

/**
 * Format file size in bytes to human-readable.
 * @param {number} bytes
 * @returns {string} e.g. "35.4 MB"
 */
export function formatFileSize(bytes) {
  if (bytes == null) return "—";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}
