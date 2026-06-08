import { useEffect, useRef, useState, useCallback } from "react";
import { getTask } from "../api";

/**
 * Polls GET /api/tasks/:taskId for status updates.
 *
 * @param {string|null} taskId
 * @param {object} opts
 * @param {function} opts.onComplete - called when status reaches completed/failed
 * @param {function} opts.onUpdate - called on every poll with (task, prevTask)
 * @param {number} opts.interval - poll interval in ms (default 2000)
 * @returns {{ task: object|null, isPolling: boolean, error: string|null }}
 */
export function useTaskPolling(taskId, opts = {}) {
  const { onComplete, onUpdate, interval = 2000 } = opts;
  const [task, setTask] = useState(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState(null);
  const prevTaskRef = useRef(null);

  /* Stable callback refs to avoid re-triggering useEffect */
  const onCompleteRef = useRef(onComplete);
  const onUpdateRef = useRef(onUpdate);
  onCompleteRef.current = onComplete;
  onUpdateRef.current = onUpdate;

  useEffect(() => {
    if (!taskId) {
      setTask(null);
      setIsPolling(false);
      setError(null);
      prevTaskRef.current = null;
      return;
    }

    let active = true;
    let timer;

    const poll = async () => {
      try {
        const data = await getTask(taskId);
        if (!active) return;

        const t = data.task;
        setTask(t);
        setIsPolling(true);
        setError(null);

        /* Fire onUpdate with stage-change detection */
        const prev = prevTaskRef.current;
        onUpdateRef.current?.(t, prev);
        prevTaskRef.current = t;

        if (t.status === "completed" || t.status === "failed") {
          setIsPolling(false);
          onCompleteRef.current?.(t);
          return;
        }

        timer = setTimeout(poll, interval);
      } catch (err) {
        if (!active) return;
        setError(err.message);
        timer = setTimeout(poll, Math.max(interval * 2, 5000));
      }
    };

    poll();

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [taskId, interval]);

  return { task, isPolling, error };
}

/**
 * Pre-defined stage-to-timeline step mapping.
 * Returns step index 1-7.
 */
const STAGE_STEP_MAP = {
  pending: 1, uploading: 1,
  video_extract: 1, video_select: 1, video_finalize: 1, video_complete: 1,
  sfm_extract_features: 2, sfm_match_features: 2,
  sfm_sparse: 3, sfm_complete: 3,
  mvs_depth: 4, mvs_complete: 4, patch_match: 4, undistort: 4,
  fusion: 5, stereo_fusion: 5,
  convert: 6, conversion_complete: 6,
  complete: 7,
};

/** Human-readable stage names (Chinese) */
export const STAGE_NAMES = {
  pending: "等待开始...",
  uploading: "正在上传图片...",
  video_extract: "正在从视频提取帧...",
  video_select: "正在筛选高质量帧...",
  video_finalize: "正在保存帧...",
  video_complete: "视频预处理完成",
  sfm_extract_features: "正在提取图像特征",
  sfm_match_features: "正在匹配特征点",
  sfm_sparse: "正在计算相机位姿 (SfM)",
  sfm_complete: "相机位姿估计完成",
  convert: "正在准备深度学习数据",
  conversion_complete: "数据转换完成",
  undistort: "正在去畸变处理...",
  patch_match: "PatchMatch 立体匹配中...",
  stereo_fusion: "正在融合深度图...",
  mvs_depth: "AI 模型深度估计中",
  mvs_complete: "深度图生成完成",
  fusion: "正在融合生成三维点云",
  complete: "重建完成！",
  failed: "重建失败",
  error: "发生错误",
};

/** Timeline step labels */
export const TIMELINE_STEPS = [
  { step: 1, label: "上传" },
  { step: 2, label: "特征提取" },
  { step: 3, label: "SfM 重建" },
  { step: 4, label: "深度估计" },
  { step: 5, label: "稠密融合" },
  { step: 6, label: "点云生成" },
  { step: 7, label: "完成" },
];

/**
 * Map a task stage to a timeline step (1-7).
 */
export function getTimelineStep(stage) {
  return STAGE_STEP_MAP[stage] || 1;
}
