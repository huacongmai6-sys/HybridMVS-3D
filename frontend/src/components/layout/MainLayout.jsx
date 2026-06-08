import { useState } from "react";
import "../../styles/layout.css";

export default function MainLayout({ sidebar, children }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`main-layout${collapsed ? " sidebar-collapsed" : ""}`}>
      <aside className="sidebar-col">
        {/* Toggle button pinned to right edge of sidebar */}
        <button
          className="sidebar-toggle"
          onClick={() => setCollapsed((v) => !v)}
          title={collapsed ? "展开面板" : "收起面板"}
        >
          <svg
            width="14" height="14" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round"
            style={{
              transform: collapsed ? "rotate(0deg)" : "rotate(180deg)",
              transition: "transform 0.25s var(--ease-out)",
            }}
          >
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>

        <div className="sidebar-inner">
          {sidebar}
        </div>
      </aside>

      <section className="viewer-col">{children}</section>
    </div>
  );
}
