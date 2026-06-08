import ParticleField from "../components/landing/ParticleField";
import HeroContent from "../components/landing/HeroContent";
import "../styles/landing.css";

export default function LandingPage({ onNavigate }) {
  return (
    <div className="landing-page">
      <ParticleField />
      <HeroContent onStart={() => onNavigate("reconstruct")} />
    </div>
  );
}
