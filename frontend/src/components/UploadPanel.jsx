import { useState, useRef } from "react";
import { uploadImages, uploadVideo } from "../api";

const DENSITY_OPTIONS = [
  { label: "稀疏", frames: 15, desc: "约15帧，速度优先" },
  { label: "标准", frames: 30, desc: "约30帧，推荐平衡" },
  { label: "密集", frames: 60, desc: "约60帧，质量优先" },
];

export default function UploadPanel({ onTaskCreated }) {
  // Image mode
  const [files, setFiles] = useState([]);
  // Video mode
  const [videoFile, setVideoFile] = useState(null);
  const [targetFrames, setTargetFrames] = useState(30);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState(null);
  // Shared
  const [inputType, setInputType] = useState("images");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const imageInputRef = useRef(null);
  const videoInputRef = useRef(null);

  // ── Image mode handlers ─────────────────────────────────────
  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (inputType === "images") {
      const dropped = Array.from(e.dataTransfer.files).filter(
        (f) => f.type.startsWith("image/")
      );
      setFiles((prev) => [...prev, ...dropped]);
    } else {
      const vid = Array.from(e.dataTransfer.files).find(
        (f) => f.type.startsWith("video/")
      );
      if (vid) setVideoFile(vid);
    }
  };

  const handleImageSelect = (e) => {
    const selected = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...selected]);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // ── Video mode handlers ─────────────────────────────────────
  const handleVideoSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setVideoFile(file);
    if (videoPreviewUrl) URL.revokeObjectURL(videoPreviewUrl);
    setVideoPreviewUrl(URL.createObjectURL(file));
  };

  const removeVideo = () => {
    setVideoFile(null);
    if (videoPreviewUrl) URL.revokeObjectURL(videoPreviewUrl);
    setVideoPreviewUrl(null);
  };

  // ── Submit ──────────────────────────────────────────────────
  const handleUpload = async () => {
    setUploading(true);
    try {
      let result;
      if (inputType === "video" && videoFile) {
        result = await uploadVideo(videoFile, "high", "colmap", targetFrames);
      } else if (files.length > 0) {
        result = await uploadImages(files);
      } else {
        return;
      }
      onTaskCreated?.(result.task);
      setFiles([]);
      removeVideo();
    } catch (err) {
      alert("上传失败: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const canUpload =
    (inputType === "images" && files.length > 0) ||
    (inputType === "video" && videoFile);

  return (
    <div className="upload-panel">
      <h2>上传数据</h2>
      <p>选择同一场景的多视角图片或录制视频进行三维重建</p>

      {/* ── Tab switcher ─────────────────────────────────── */}
      <div className="input-tabs">
        <button
          className={`tab-btn ${inputType === "images" ? "active" : ""}`}
          onClick={() => setInputType("images")}
        >
          📷 上传图片
        </button>
        <button
          className={`tab-btn ${inputType === "video" ? "active" : ""}`}
          onClick={() => setInputType("video")}
        >
          🎬 上传视频
        </button>
      </div>

      {/* ── Image mode ────────────────────────────────────── */}
      {inputType === "images" && (
        <>
          <div
            className={`drop-zone ${dragOver ? "drag-over" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => imageInputRef.current?.click()}
          >
            <span className="drop-icon">+</span>
            <p>拖拽图片到此处，或点击选择文件</p>
            <p className="hint">支持格式：JPG、PNG、TIFF、BMP</p>
          </div>

          <input
            ref={imageInputRef}
            type="file"
            multiple
            accept="image/*"
            style={{ display: "none" }}
            onChange={handleImageSelect}
          />

          {files.length > 0 && (
            <div className="file-list">
              <h4>{files.length} 张图片已选择</h4>
              <div className="file-grid">
                {files.map((f, i) => (
                  <div key={i} className="file-item">
                    <img src={URL.createObjectURL(f)} alt={f.name} />
                    <span className="file-name">{f.name}</span>
                    <button className="btn-remove" onClick={() => removeFile(i)}>
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Video mode ────────────────────────────────────── */}
      {inputType === "video" && (
        <>
          {!videoFile ? (
            <div
              className={`drop-zone ${dragOver ? "drag-over" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const vid = Array.from(e.dataTransfer.files).find(
                  (f) => f.type.startsWith("video/")
                );
                if (vid) {
                  setVideoFile(vid);
                  setVideoPreviewUrl(URL.createObjectURL(vid));
                }
              }}
              onClick={() => videoInputRef.current?.click()}
            >
              <span className="drop-icon">🎬</span>
              <p>拖拽视频到此处，或点击选择文件</p>
              <p className="hint">
                支持格式：MP4、MOV、AVI、MKV、WebM（建议1-2分钟）
              </p>
            </div>
          ) : (
            <div className="video-preview-section">
              <div className="video-preview-card">
                <video
                  src={videoPreviewUrl}
                  controls
                  muted
                  className="video-preview"
                />
                <div className="video-info">
                  <span className="video-name">{videoFile.name}</span>
                  <span className="video-size">
                    {(videoFile.size / (1024 * 1024)).toFixed(1)} MB
                  </span>
                </div>
                <button className="btn-remove-video" onClick={removeVideo}>
                  移除视频
                </button>
              </div>

              <h4>采样密度</h4>
              <div className="density-options">
                {DENSITY_OPTIONS.map((opt) => (
                  <label
                    key={opt.frames}
                    className={`density-option ${
                      targetFrames === opt.frames ? "selected" : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="density"
                      value={opt.frames}
                      checked={targetFrames === opt.frames}
                      onChange={() => setTargetFrames(opt.frames)}
                    />
                    <span className="density-label">{opt.label}</span>
                    <span className="density-desc">{opt.desc}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <input
            ref={videoInputRef}
            type="file"
            accept="video/*"
            style={{ display: "none" }}
            onChange={handleVideoSelect}
          />
        </>
      )}

      {/* ── Submit button ─────────────────────────────────── */}
      {canUpload && (
        <button
          className="btn btn-primary"
          onClick={handleUpload}
          disabled={uploading}
        >
          {uploading ? "上传中..." : "开始重建"}
        </button>
      )}
    </div>
  );
}
