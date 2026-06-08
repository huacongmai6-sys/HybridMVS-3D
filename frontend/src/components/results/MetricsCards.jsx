import { formatCount, formatDuration, formatPercent } from "../../utils/formatters";
import "../../styles/results.css";

/**
 * MetricsCards — Display key reconstruction statistics in a card row.
 * @param {{ pointData: object|null, completedTask: object|null }} props
 */
export default function MetricsCards({ pointData, completedTask }) {
  if (!completedTask && !pointData) return null;

  const cards = [
    {
      icon: "●",
      label: "顶点数",
      value: pointData ? formatCount(pointData.count) : "—",
      sub: "稠密点云",
    },
    {
      icon: "◈",
      label: "密度",
      value: pointData
        ? formatCount(
            Math.round(pointData.count / Math.max(pointData.extent ** 3, 0.001))
          ) + "/m³"
        : "—",
      sub: "平均密度",
    },
    {
      icon: "✓",
      label: "置信度",
      value: completedTask?.stats?.avg_confidence
        ? formatPercent(completedTask.stats.avg_confidence)
        : "—",
      sub: "平均置信度",
    },
    {
      icon: "▣",
      label: "图片数",
      value: completedTask?.num_images ?? "—",
      sub: "输入视角",
    },
    {
      icon: "⏱",
      label: "耗时",
      value: completedTask?.stats?.duration
        ? formatDuration(completedTask.stats.duration)
        : "—",
      sub: "估计时间",
    },
  ];

  return (
    <div className="metrics-cards">
      {cards.map((card, i) => (
        <div key={i} className="metric-card glass-card">
          <span className="metric-icon">{card.icon}</span>
          <div className="metric-body">
            <span className="metric-label">{card.label}</span>
            <span className="metric-value text-mono">{card.value}</span>
            <span className="metric-sub text-muted">{card.sub}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
