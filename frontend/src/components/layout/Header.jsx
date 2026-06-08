import "../../styles/layout.css";

export default function Header() {
  return (
    <header className="app-header">
      <div className="header-left">
        {/* 3D cube icon */}
        <svg className="header-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
          <path d="M2 17l10 5 10-5"/>
          <path d="M2 12l10 5 10-5"/>
        </svg>
        <div className="header-title">
          <span>Hybrid</span>MVS
        </div>
      </div>

      <div className="header-right">
        <a
          className="header-nav-link"
          href="https://github.com/huacongmai6-sys/HybridMVS-3D"
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </a>
      </div>
    </header>
  );
}
