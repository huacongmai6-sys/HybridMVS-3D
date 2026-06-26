import "./HeroContent.css";

export default function HeroContent({ onStart }) {
  return (
    <div className="hero-content">
      {/* ── Badge ─────────────────────────────── */}
      <span className="hero-badge fade-in-up">3D Reconstruction</span>

      {/* ── Title with breathing glow ─────────── */}
      <div className="hero-title-wrapper fade-in-up stagger-1">
        <h1 className="hero-title">
          <span className="hero-title-brand">Hybrid</span>
          <span className="hero-title-rest">MVS</span>
        </h1>
      </div>

      {/* ── Subtitle ──────────────────────────── */}
      <p className="hero-subtitle fade-in-up stagger-2">
        Hybrid 3D Reconstruction System
      </p>
      <p className="hero-subtitle-cn fade-in-up stagger-2">
        COLMAP SfM + CasMVSNet + DenseFusion
      </p>

      {/* ── CTA ───────────────────────────────── */}
      <div className="hero-cta fade-in-up stagger-3">
        <button className="btn-primary hero-cta-btn" onClick={onStart}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          开始重建
        </button>
      </div>

      {/* ── Feature highlights ────────────────── */}
      <div className="feature-grid fade-in-up stagger-4">
        <div className="glass-card feature-card">
          <div className="feature-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
              <line x1="12" y1="22" x2="12" y2="15.5"/>
              <polyline points="22 8.5 12 15.5 2 8.5"/>
            </svg>
          </div>
          <h3>深度学习 MVS</h3>
          <p>CasMVSNet 级联深度估计，弱纹理区域表现优秀</p>
        </div>

        <div className="glass-card feature-card">
          <div className="feature-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
              <line x1="9" y1="9" x2="9.01" y2="9"/>
              <line x1="15" y1="9" x2="15.01" y2="9"/>
            </svg>
          </div>
          <h3>COLMAP SfM</h3>
          <p>成熟的运动恢复结构管线，稳定可靠的重建质量</p>
        </div>

        <div className="glass-card feature-card">
          <div className="feature-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="17 1 21 5 17 9"/>
              <path d="M3 11V9a4 4 0 014-4h14"/>
              <polyline points="7 23 3 19 7 15"/>
              <path d="M21 13v2a4 4 0 01-4 4H3"/>
            </svg>
          </div>
          <h3>多输入支持</h3>
          <p>支持多视角图像上传与视频智能抽帧</p>
        </div>

        <div className="glass-card feature-card">
          <div className="feature-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          <h3>3D 可视化</h3>
          <p>基于 Three.js 的实时点云查看器，支持旋转缩放平移</p>
        </div>
      </div>
    </div>
  );
}
