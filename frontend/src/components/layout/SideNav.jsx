import { useState, useRef } from "react";
import { useAppContext } from "../../context/AppContext";
import "../../styles/layout.css";

export default function SideNav({ onAboutOpen }) {
  const { glassEnabled, setGlassEnabled } = useAppContext();
  const aboutBtnRef = useRef(null);

  return (
    <nav id="side-nav">
      <ul className="side-nav-items">
        {/* Logo */}
        <li className="side-nav-logo">
          <span className="side-nav-item-inner">
            <span className="side-nav-icon-wrapper">
              <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="1.6"
                   strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </span>
            <span className="side-nav-text">HybridMVS</span>
          </span>
        </li>

        {/* About */}
        <li className="side-nav-item">
          <button
            className="side-nav-item-inner"
            onClick={onAboutOpen}
            ref={aboutBtnRef}
          >
            <span className="side-nav-icon-wrapper">
              <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="1.6"
                   strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
            </span>
            <span className="side-nav-text">About</span>
          </button>
        </li>

        {/* GitHub */}
        <li className="side-nav-item">
          <a
            className="side-nav-item-inner"
            href="https://github.com/huacongmai6-sys/HybridMVS-3D"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span className="side-nav-icon-wrapper">
              <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="1.6"
                   strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 18 22 12 16 6"/>
                <polyline points="8 6 2 12 8 18"/>
              </svg>
            </span>
            <span className="side-nav-text">GitHub</span>
          </a>
        </li>

        {/* Glass mode toggle */}
        <li className="side-nav-item">
          <button
            className="side-nav-item-inner"
            onClick={() => setGlassEnabled(!glassEnabled)}
          >
            <span className="side-nav-icon-wrapper">
              {glassEnabled ? (
                <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" strokeWidth="1.6"
                     strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              ) : (
                <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" strokeWidth="1.6"
                     strokeLinecap="round" strokeLinejoin="round">
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

        {/* Version */}
        <li className="side-nav-version">
          <span className="side-nav-item-inner">
            <span className="side-nav-icon-wrapper">
              <svg className="side-nav-svg" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="1.6"
                   strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/>
                <line x1="7" y1="7" x2="7.01" y2="7"/>
              </svg>
            </span>
            <span className="side-nav-text">v1.16</span>
          </span>
        </li>
      </ul>
    </nav>
  );
}
