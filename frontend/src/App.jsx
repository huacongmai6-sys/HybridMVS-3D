import { useState } from "react";
import { AppProvider, useAppContext } from "./context/AppContext";
import ParticleField from "./components/landing/ParticleField";
import SideNav from "./components/layout/SideNav";
import LandingPage from "./pages/LandingPage";
import MainPage from "./pages/MainPage";
import ComparisonPage from "./pages/ComparisonPage";
import "./styles/layout.css";

function AppInner() {
  const [page, setPage] = useState("landing");
  const [aboutOpen, setAboutOpen] = useState(false);
  const { glassEnabled } = useAppContext();

  return (
    <>
      {/* ── Particle background (always, behind everything) ── */}
      <ParticleField />

      {/* ── Collapsible side navigation ──────────────── */}
      <SideNav onAboutOpen={() => setAboutOpen(true)} onNavigate={setPage} />

      {/* ── Main content ─────────────────────────────── */}
      {page === "landing" && <LandingPage onNavigate={setPage} />}
      {page === "reconstruct" && <MainPage />}
      {page === "comparison" && <ComparisonPage onNavigate={setPage} />}

      {/* ── About modal (redesigned: fade-in / fade-out) ── */}
      {aboutOpen && <AboutModal onClose={() => setAboutOpen(false)} />}
    </>
  );
}

/* ═══════════════════════════════════════════════════════
   About Modal — Redesigned fade-in/fade-out
   ═══════════════════════════════════════════════════════ */
function AboutModal({ onClose }) {
  const [closing, setClosing] = useState(false);

  const handleClose = () => {
    setClosing(true);
    setTimeout(onClose, 300);
  };

  return (
    <div
      className={`about-overlay${closing ? " closing" : ""}`}
      onClick={handleClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 10000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0,0,0,0.6)",
        backdropFilter: "blur(4px)",
        animation: closing ? "fadeIn 0.3s ease reverse both" : "fadeIn 0.3s ease both",
      }}
    >
      <div
        className={`about-modal${closing ? " closing" : ""}`}
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-lg)",
          padding: "2rem 2.5rem",
          maxWidth: 560,
          width: "90%",
          boxShadow: "var(--shadow-elevated)",
          animation: closing
            ? "fadeInScale 0.3s ease reverse both"
            : "scaleInBounce 0.4s var(--ease-out) both",
          position: "relative",
        }}
      >
        {/* Close button */}
        <button
          onClick={handleClose}
          style={{
            position: "absolute",
            top: 14,
            right: 18,
            background: "none",
            border: "none",
            color: "var(--text-muted)",
            fontSize: "1.3rem",
            cursor: "pointer",
            padding: "4px 8px",
            borderRadius: "var(--radius-sm)",
            transition: "color 0.15s ease",
          }}
          onMouseEnter={(e) => (e.target.style.color = "var(--text-bright)")}
          onMouseLeave={(e) => (e.target.style.color = "var(--text-muted)")}
        >
          ✕
        </button>

        <h2
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "1.4rem",
            fontWeight: 700,
            color: "var(--text-bright)",
            marginBottom: "0.3rem",
          }}
        >
          HybridMVS
        </h2>
        <p
          style={{
            fontSize: "0.9rem",
            color: "var(--primary)",
            marginBottom: "1rem",
          }}
        >
          基于 COLMAP 与深度学习的混合式三维重建系统
        </p>

        <p style={{ fontSize: "0.85rem", color: "var(--text-body)", lineHeight: 1.6, marginBottom: "1.2rem" }}>
          HybridMVS 结合了 COLMAP 运动恢复结构（SfM）与深度学习多视图立体匹配（MVS），
          支持从多视角图像或视频中自动生成高质量稠密点云与网格模型。
          系统提供图像上传与视频抽帧两种输入方式，内置 COLMAP 稀疏重建、
          PatchMatch 稠密重建以及 CasMVSNet 深度估计三条重建管线。
        </p>

        <h3
          style={{
            fontSize: "0.85rem",
            fontWeight: 600,
            color: "var(--text-heading)",
            marginBottom: "0.5rem",
          }}
        >
          使用流程
        </h3>
        <ol
          style={{
            fontSize: "0.82rem",
            color: "var(--text-body)",
            paddingLeft: "1.2rem",
            marginBottom: "1.2rem",
            lineHeight: 1.7,
          }}
        >
          <li>上传多视角图像或视频</li>
          <li>选择重建密度与参数</li>
          <li>等待后台处理完成</li>
          <li>在 3D 查看器中预览点云</li>
          <li>下载 PLY / OBJ 结果文件</li>
        </ol>

        <h3
          style={{
            fontSize: "0.85rem",
            fontWeight: 600,
            color: "var(--text-heading)",
            marginBottom: "0.5rem",
          }}
        >
          技术栈
        </h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["COLMAP v4.1", "PyTorch 2.7", "CasMVSNet", "Flask", "React 19", "Three.js"].map(
            (tech) => (
              <span
                key={tech}
                style={{
                  padding: "4px 12px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg-raised)",
                  color: "var(--text-muted)",
                  fontSize: "0.75rem",
                  fontFamily: "var(--font-mono)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {tech}
              </span>
            )
          )}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   App (public export) — wraps AppInner with AppProvider
   ═══════════════════════════════════════════════════ */
export default function App() {
  return (
    <AppProvider>
      <AppInner />
    </AppProvider>
  );
}
