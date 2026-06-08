import { useState, useCallback, useRef } from "react";
import { useAppContext } from "../context/AppContext";
import { useTaskPolling, STAGE_NAMES } from "../hooks/useTaskPolling";
import { getDownloadUrl } from "../api";
import Header from "../components/layout/Header";
import MainLayout from "../components/layout/MainLayout";
import UploadPanel from "../components/upload/UploadPanel";
import ProgressTimeline from "../components/progress/ProgressTimeline";
import ProgressBar from "../components/progress/ProgressBar";
import LogWindow from "../components/progress/LogWindow";
import Viewer3D from "../components/viewer/Viewer3D";
import ResultsPanel from "../components/results/ResultsPanel";

function timeStamp() {
  const now = new Date();
  return now.toTimeString().slice(0, 8);
}

export default function MainPage() {
  const { taskId, completedTask, setTaskId, setCompletedTask } = useAppContext();
  const [logs, setLogs] = useState([]);
  const prevStageRef = useRef(null);

  /* ── Polling callback: build logs from stage changes ── */
  const handleUpdate = useCallback((task, prevTask) => {
    const prevStage = prevStageRef.current;
    if (task.stage && task.stage !== prevStage) {
      const name = STAGE_NAMES[task.stage] || task.stage;
      setLogs((l) => [
        ...l,
        {
          time: timeStamp(),
          message: `[${task.stage}] ${name}`,
          type: task.status === "failed" ? "error" : "info",
        },
      ]);
      prevStageRef.current = task.stage;
    }
  }, []);

  const handleComplete = useCallback((task) => {
    setCompletedTask(task);
    setLogs((l) => [
      ...l,
      {
        time: timeStamp(),
        message: task.status === "failed"
          ? `重建失败: ${task.error_message || "未知错误"}`
          : "重建完成！点云已生成",
        type: task.status === "failed" ? "error" : "info",
      },
    ]);
  }, [setCompletedTask]);

  const { task, isPolling } = useTaskPolling(taskId, {
    onComplete: handleComplete,
    onUpdate: handleUpdate,
  });

  const handleTaskCreated = (task) => {
    setTaskId(task.id);
    setCompletedTask(null);
    setLogs([
      {
        time: timeStamp(),
        message: `任务已创建 | ${task.num_images || 0} 张图片`,
        type: "info",
      },
    ]);
    prevStageRef.current = null;
  };

  return (
    <div className="app-shell">
      <Header />

      <MainLayout
        sidebar={
          <>
            {/* Hide upload when task is running */}
            {!taskId && <UploadPanel onTaskCreated={handleTaskCreated} />}

            {/* Progress during reconstruction */}
            {taskId && !completedTask && task && (
              <>
                <ProgressBar percent={task.progress || 0} status={task.status} />
                <ProgressTimeline
                  stage={task.stage}
                  status={task.status}
                  progress={task.progress || 0}
                />
                <LogWindow logs={logs} />
              </>
            )}

            {/* Results when done */}
            {completedTask && (
              <ResultsPanel
                completedTask={completedTask}
              />
            )}

            {taskId && isPolling && !task && (
              <div className="glass-card" style={{ padding: "1rem", textAlign: "center" }}>
                <p style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                  正在连接…
                </p>
              </div>
            )}
          </>
        }
      >
        <Viewer3D
          modelUrl={
            completedTask?.dense_ply
              ? getDownloadUrl(completedTask.id, "ply")
              : null
          }
          stats={completedTask ? {
            num_images: completedTask.num_images,
          } : null}
        />
      </MainLayout>
    </div>
  );
}
