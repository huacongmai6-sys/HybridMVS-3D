import { useRef, useEffect, useState, useCallback } from "react";

/**
 * LogWindow — Terminal-style scrollable log view.
 * @param {{ logs: Array<{time: string, message: string, type: string}> }} props
 */
export default function LogWindow({ logs = [] }) {
  const bodyRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  /* Auto-scroll to bottom when new logs arrive */
  useEffect(() => {
    if (autoScroll && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleClear = () => {
    /* logs are managed by parent — clear is a no-op callback */
  };

  /* Detect if user scrolled up to disable auto-scroll */
  const handleScroll = useCallback(() => {
    if (!bodyRef.current) return;
    const el = bodyRef.current;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 20;
    setAutoScroll(atBottom);
  }, []);

  return (
    <div className="log-window glass-card">
      <div className="log-header">
        <span className="log-title">输出</span>
        <div className="log-actions">
          <button
            className={`log-action-btn${autoScroll ? " active" : ""}`}
            onClick={() => setAutoScroll(!autoScroll)}
            title={autoScroll ? "自动滚动：开" : "自动滚动：关"}
          >
            自动
          </button>
        </div>
      </div>

      <div className="log-body" ref={bodyRef} onScroll={handleScroll}>
        {logs.length === 0 ? (
          <div className="log-empty">等待任务开始…</div>
        ) : (
          logs.map((entry, i) => (
            <div key={i} className={`log-entry${entry.type === "error" ? " error" : ""}`}>
              <span className="log-time">{entry.time}</span>
              <span className="log-msg">{entry.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
