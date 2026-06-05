import { useState, Fragment } from "react";
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
      <div className="app">
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
    </>
  );
}
