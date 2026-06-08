import { getDownloadUrl } from "../../api";
import "../../styles/results.css";

/**
 * DownloadPanel — Download buttons for reconstruction output files.
 * @param {{ taskId: string, densePly: boolean, denseObj: boolean, sparsePly: boolean, stats: boolean }} props
 */
export default function DownloadPanel({
  taskId,
  densePly = false,
  denseObj = false,
  sparsePly = false,
  stats = false,
}) {
  if (!taskId) return null;

  const items = [
    { label: "PLY 稠密点云", type: "ply", show: densePly, icon: "⬡" },
    { label: "OBJ 网格模型", type: "obj", show: denseObj, icon: "◫" },
    { label: "稀疏点云", type: "sparse_ply", show: sparsePly, icon: "◦◦◦" },
    { label: "统计数据 (JSON)", type: "stats", show: stats, icon: "{}" },
  ].filter((item) => item.show);

  if (items.length === 0) return null;

  return (
    <div className="download-panel glass-card">
      <h3 className="download-title text-mono">下载结果</h3>
      <div className="download-links">
        {items.map((item) => (
          <a
            key={item.type}
            className="btn-download"
            href={getDownloadUrl(taskId, item.type)}
            download
          >
            <span className="download-icon">{item.icon}</span>
            {item.label}
          </a>
        ))}
      </div>
    </div>
  );
}
