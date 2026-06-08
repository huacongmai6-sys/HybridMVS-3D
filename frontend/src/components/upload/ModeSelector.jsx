import { useAppContext } from "../../context/AppContext";
import "../../styles/upload.css";

const MODES = [
  {
    id: "colmap",
    title: "COLMAP PatchMatch",
    subtitle: "稳定 · 快速 · 生产级",
    description: "基于COLMAP的传统稠密重建，适用于常规场景，CPU友好。",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
    ),
    badge: "推荐",
    badgeClass: "badge-primary",
  },
  {
    id: "mvs",
    title: "CasMVSNet",
    subtitle: "高精度 · GPU加速 · 深度学习",
    description: "基于深度学习的多视图立体匹配，弱纹理区域表现优秀。",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
    ),
    badge: "实验性",
    badgeClass: "badge-highlight",
  },
  {
    id: "patchmatchnet",
    title: "PatchMatchNet",
    subtitle: "轻量 · 推理快 · 即将推出",
    description: "基于学习的轻量级PatchMatch，迭代传播优化，速度快。",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
      </svg>
    ),
    badge: "即将推出",
    badgeClass: "badge-muted",
    disabled: true,
  },
];

export default function ModeSelector() {
  const { reconstructionMode, setReconstructionMode } = useAppContext();

  return (
    <div className="mode-selector glass-card">
      <h3 className="mode-selector-title text-mono">
        重建模式
      </h3>
      <div className="mode-cards">
        {MODES.map((mode) => {
          const isSelected = reconstructionMode === mode.id;
          const isDisabled = mode.disabled;

          return (
            <button
              key={mode.id}
              className={`mode-card${isSelected ? " selected" : ""}${isDisabled ? " disabled" : ""}`}
              onClick={() => !isDisabled && setReconstructionMode(mode.id)}
              disabled={isDisabled}
              title={isDisabled ? "此模式即将推出，敬请期待" : ""}
            >
              <div className="mode-card-icon">{mode.icon}</div>
              <div className="mode-card-body">
                <span className="mode-card-title">{mode.title}</span>
                <span className="mode-card-subtitle">{mode.subtitle}</span>
                <span className="mode-card-desc">{mode.description}</span>
              </div>
              <span className={`mode-card-badge ${mode.badgeClass}`}>{mode.badge}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
