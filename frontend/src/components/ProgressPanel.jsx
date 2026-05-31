import { useEffect, useState } from "react";
import { getTask } from "../api";

const STAGE_NAMES = {
  pending: "等待开始...",
  uploading: "正在上传图片...",
  sfm_extract_features: "正在提取图像特征",
  sfm_match_features: "正在匹配特征点",
  sfm_sparse: "正在计算相机位姿 (SfM)",
  sfm_complete: "相机位姿估计完成",
  convert: "正在准备深度学习数据",
  mvs_depth: "AI 模型深度估计中",
  mvs_complete: "深度图生成完成",
  fusion: "正在融合生成三维点云",
  complete: "重建完成！",
  failed: "重建失败",
};

export default function ProgressPanel({ taskId, onComplete }) {
  const [task, setTask] = useState(null);

  useEffect(() => {
    if (!taskId) return;
    let active = true;
    let timer;

    const poll = async () => {
      try {
        const data = await getTask(taskId);
        if (!active) return;
        setTask(data.task);

        if (data.task.status === "completed" || data.task.status === "failed") {
          onComplete?.(data.task);
          return;
        }
        timer = setTimeout(poll, 2000);
      } catch {
        timer = setTimeout(poll, 5000);
      }
    };

    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [taskId]);

  if (!task) return null;

  const pct = task.progress || 0;
  const stageName = STAGE_NAMES[task.stage] || task.stage || "Processing...";
  const isFailed = task.status === "failed";
  const isDone = task.status === "completed";

  return (
    <div className={`progress-panel ${isFailed ? "failed" : isDone ? "done" : ""}`}>
      <h3>{isFailed ? "出错" : isDone ? "重建完成！" : "正在重建..."}</h3>

      <div className="progress-bar-container">
        <div
          className={`progress-bar ${isFailed ? "bar-failed" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="progress-info">
        <span className="stage-name">{stageName}</span>
        <span className="progress-pct">{pct}%</span>
      </div>

      {isFailed && task.error_message && (
        <div className="error-message">{task.error_message}</div>
      )}
    </div>
  );
}
