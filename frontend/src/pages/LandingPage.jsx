import GlowOrbs from "../components/landing/GlowOrbs";
import NoiseOverlay from "../components/landing/NoiseOverlay";
import HeroContent from "../components/landing/HeroContent";
import "../styles/landing.css";

export default function LandingPage({ onNavigate }) {
  return (
    <div className="landing-page">
      {/* ── 氛围背景层 (z=0) ──────────────────── */}
      {/* DotWaveBackground 由 App.jsx 全局渲染，此处不重复 */}
      <GlowOrbs />
      <NoiseOverlay />

      {/* ── 主内容层 (z=1) ──────────────────── */}
      <HeroContent onStart={() => onNavigate("reconstruct")} />
    </div>
  );
}
