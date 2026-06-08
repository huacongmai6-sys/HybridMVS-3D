import { useState, useRef, Fragment } from "react";
import UploadPanel from "./components/UploadPanel";
import ProgressPanel from "./components/ProgressPanel";
import DepthMapPanel from "./components/DepthMapPanel";
import DotWaveBackground from "./components/DotWaveBackground";
import Viewer3D from "./components/Viewer3D";
import { getDownloadUrl } from "./api";
import "./App.css";

export default function App() {
  const [taskId, setTaskId] = useState(null);
  const [completedTask, setCompletedTask] = useState(null);
  const [glassEnabled, setGlassEnabled] = useState(true);

  // ── About 弹窗：卡片展开过渡动画（参考 card-expansion 模式）──
  const aboutBtnRef = useRef(null);
  const [aboutState, setAboutState] = useState(null);
  // null                     → 关闭
  // { phase:'expanding', ... } → cover 正在展开
  // { phase:'open', ... }      → 弹窗可见
  // { phase:'shrinking', ... } → cover 正在收回

  const openAbout = () => {
    const btn = aboutBtnRef.current;
    // 获取侧边栏按钮的屏幕位置（若取不到则回退到中心点）
    const rect = btn
      ? btn.getBoundingClientRect()
      : { left: 0, top: window.innerHeight / 2, width: 1, height: 1 };
    const W = window.innerWidth;
    const H = window.innerHeight;

    const scaleX = W / Math.max(rect.width, 1);
    const scaleY = H / Math.max(rect.height, 1);
    const offsetX = (W / 2 - rect.width / 2 - rect.left) / scaleX;
    const offsetY = (H / 2 - rect.height / 2 - rect.top) / scaleY;

    setAboutState({
      phase: "expanding",
      from: {
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
      },
      toTransform: `scaleX(${scaleX}) scaleY(${scaleY}) translate3d(${offsetX}px, ${offsetY}px, 0px)`,
    });

    // 下一帧触发展开（CSS transition 接管动画）
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setAboutState((prev) =>
          prev ? { ...prev, expanded: true } : null
        );
      });
    });

    // cover 展开完成后显示内容
    setTimeout(() => {
      setAboutState((prev) =>
        prev ? { ...prev, phase: "open" } : null
      );
    }, 520);
  };

  const closeAbout = () => {
    // 保持展开状态，通过 opacity 淡出（避免缩回时出现黑色方块）
    setAboutState((prev) =>
      prev ? { ...prev, phase: "shrinking" } : null
    );
    // 淡出动画完成后清理（匹配最长动画 0.55s）
    setTimeout(() => {
      setAboutState(null);
    }, 580);
  };

  const handleTaskCreated = (task) => {
    setTaskId(task.id);
    setCompletedTask(null);
  };

  const handleComplete = (task) => {
    setCompletedTask(task);
  };

  return (
    <>
      <DotWaveBackground />

      {/* ── 侧边导航栏 ────────────────────────────── */}
      <nav id="side-nav">
        <ul className="side-nav-items">
          {/* Logo — 3D 立方体 */}
          <li className="side-nav-logo">
            <span className="side-nav-item-inner">
              <span className="side-nav-icon-wrapper">
                <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                  <path d="M2 17l10 5 10-5"/>
                  <path d="M2 12l10 5 10-5"/>
                </svg>
              </span>
              <span className="side-nav-text">HybridMVS</span>
            </span>
          </li>
          {/* About — info circle */}
          <li className="side-nav-item">
            <button className="side-nav-item-inner" onClick={openAbout} ref={aboutBtnRef}>
              <span className="side-nav-icon-wrapper">
                <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="16" x2="12" y2="12"/>
                  <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
              </span>
              <span className="side-nav-text">About</span>
            </button>
          </li>
          {/* GitHub — code brackets */}
          <li className="side-nav-item">
            <a
              className="side-nav-item-inner"
              href="https://github.com/huacongmai6-sys/HybridMVS-3D"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="side-nav-icon-wrapper">
                <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="16 18 22 12 16 6"/>
                  <polyline points="8 6 2 12 8 18"/>
                </svg>
              </span>
              <span className="side-nav-text">GitHub</span>
            </a>
          </li>
          {/* 毛玻璃切换 — eye / layers */}
          <li className="side-nav-item">
            <button
              className="side-nav-item-inner"
              onClick={() => setGlassEnabled((g) => !g)}
            >
              <span className="side-nav-icon-wrapper">
                {glassEnabled ? (
                  <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                ) : (
                  <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="2" width="20" height="20" rx="2"/>
                    <path d="M12 6v12M6 12h12"/>
                  </svg>
                )}
              </span>
              <span className="side-nav-text">
                {glassEnabled ? "毛玻璃" : "透明"}
              </span>
            </button>
          </li>
          {/* 版本 — tag */}
          <li className="side-nav-version">
            <span className="side-nav-item-inner">
              <span className="side-nav-icon-wrapper">
                <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/>
                  <line x1="7" y1="7" x2="7.01" y2="7"/>
                </svg>
              </span>
              <span className="side-nav-text">v1.1</span>
            </span>
          </li>
        </ul>
      </nav>

      <div className={`app${glassEnabled ? "" : " no-glass"}`}>
      <header className="app-header">
        <h1><span>Hybrid</span>MVS</h1>
        <span className="subtitle">基于COLMAP与深度学习的混合式三维重建系统</span>
      </header>

      <main className="app-main">
        <aside className="sidebar">
          <UploadPanel onTaskCreated={handleTaskCreated} />

          {taskId && (
            <ProgressPanel taskId={taskId} onComplete={handleComplete} />
          )}

          {completedTask && completedTask.depth_previews?.length > 0 && (
            <DepthMapPanel
              depthPreviews={completedTask.depth_previews}
              taskId={completedTask.id}
            />
          )}

          {completedTask && (
            <div className="download-panel">
              <h3>下载结果</h3>
              <div className="download-links">
                {completedTask.dense_ply && (
                  <a
                    className="btn btn-download"
                    href={getDownloadUrl(completedTask.id, "ply")}
                    download
                  >
                    PLY 稠密点云
                  </a>
                )}
                {completedTask.dense_obj && (
                  <a
                    className="btn btn-download"
                    href={getDownloadUrl(completedTask.id, "obj")}
                    download
                  >
                    OBJ 网格模型
                  </a>
                )}
                {completedTask.sparse_ply && (
                  <a
                    className="btn btn-download"
                    href={getDownloadUrl(completedTask.id, "sparse_ply")}
                    download
                  >
                    稀疏点云
                  </a>
                )}
              </div>
            </div>
          )}
        </aside>

        <section className="viewer-section">
          <Viewer3D
            modelUrl={
              completedTask?.dense_ply
                ? getDownloadUrl(completedTask.id, "ply")
                : null
            }
          />
        </section>
      </main>
    </div>

      {/* ── About 弹窗（卡片展开过渡动画）───────────── */}
      {aboutState && (
        <>
          {/* cover：从按钮位置展开到全屏的深色色块（关闭时原地淡出） */}
          <div
            className="about-cover"
            style={{
              position: "fixed",
              left: aboutState.from.left,
              top: aboutState.from.top,
              width: aboutState.from.width || 1,
              height: aboutState.from.height || 1,
              zIndex: 9999,
              background: "hsl(257, 11%, 14%)",
              opacity: aboutState.phase === "shrinking" ? 0 : 1,
              transform: aboutState.expanded
                ? aboutState.toTransform
                : "scaleX(1) scaleY(1) translate3d(0, 0, 0)",
              transition:
                "transform 0.5s cubic-bezier(0.175, 0.685, 0.32, 1), opacity 0.55s ease",
            }}
          />

          {/* 弹窗内容（cover 展开后才显示） */}
          {(aboutState.phase === "open" || aboutState.phase === "shrinking") && (
            <div
              className={`about-overlay${aboutState.phase === "shrinking" ? " closing" : ""}`}
              onClick={closeAbout}
            >
              <div
                className={`about-modal${aboutState.phase === "shrinking" ? " closing" : ""}`}
                onClick={(e) => e.stopPropagation()}
              >
                <button className="about-close" onClick={closeAbout}>
                  ✕
                </button>
                <h2>HybridMVS</h2>
                <p className="about-tagline">
                  基于 COLMAP 与深度学习的混合式三维重建系统
                </p>
                <p className="about-desc">
                  HybridMVS 结合了 COLMAP 运动恢复结构（SfM）与深度学习多视图立体匹配（MVS），
                  支持从多视角图像或视频中自动生成高质量稠密点云与网格模型。
                  系统提供图像上传与视频抽帧两种输入方式，内置 COLMAP 稀疏重建、
                  PatchMatch 稠密重建以及 CasMVSNet 深度估计三条重建管线。
                </p>
                <h3>使用流程</h3>
                <ol className="about-steps">
                  <li>上传多视角图像或视频</li>
                  <li>选择重建密度与参数</li>
                  <li>等待后台处理完成</li>
                  <li>在 3D 查看器中预览点云</li>
                  <li>下载 PLY / OBJ 结果文件</li>
                </ol>
                <h3>技术栈</h3>
                <div className="about-tech">
                  <span>COLMAP v4.1</span>
                  <span>PyTorch 2.7</span>
                  <span>CasMVSNet</span>
                  <span>Flask</span>
                  <span>React 19</span>
                  <span>Three.js</span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
