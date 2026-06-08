import { useState, useMemo } from "react";
import { useAppContext } from "../../context/AppContext";
import { uploadImages, uploadVideo } from "../../api";
import FileDropZone from "./FileDropZone";
import ModeSelector from "./ModeSelector";
import AdvancedSettings from "./AdvancedSettings";
import { formatFileSize } from "../../utils/formatters";
import "../../styles/upload.css";

const ACCEPT_IMAGES = "image/png,image/jpeg,image/tiff,image/bmp";
const ACCEPT_VIDEO = "video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm";

export default function UploadPanel({ onTaskCreated }) {
  const { reconstructionMode, setTaskId } = useAppContext();
  const [tab, setTab] = useState("images");

  /* ── Image mode state ──────────────────────── */
  const [imageFiles, setImageFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  /* ── Video mode state ──────────────────────── */
  const [videoFile, setVideoFile] = useState(null);
  const [density, setDensity] = useState(30);
  const densityLabels = { 15: "稀疏", 30: "标准", 60: "密集" };

  /* ── Total size ────────────────────────────── */
  const totalSize = useMemo(() => {
    if (tab === "images") {
      const bytes = imageFiles.reduce((sum, f) => sum + f.size, 0);
      return formatFileSize(bytes);
    }
    return videoFile ? formatFileSize(videoFile.size) : "—";
  }, [tab, imageFiles, videoFile]);

  /* ── Handlers ──────────────────────────────── */
  const handleImageFiles = (files) => {
    const valid = files.filter((f) =>
      /\.(png|jpg|jpeg|tiff?|bmp)$/i.test(f.name)
    );
    setImageFiles((prev) => [...prev, ...valid]);
    setUploadError(null);
  };

  const handleRemoveImage = (idx) => {
    setImageFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleClearImages = () => {
    setImageFiles([]);
  };

  const handleVideoFile = (files) => {
    setVideoFile(files[0]);
    setUploadError(null);
  };

  const handleClearVideo = () => {
    setVideoFile(null);
  };

  const handleSubmit = async () => {
    setUploadError(null);

    if (tab === "images" && imageFiles.length === 0) {
      setUploadError("请先上传至少一张图片");
      return;
    }
    if (tab === "video" && !videoFile) {
      setUploadError("请先上传一个视频文件");
      return;
    }

    setUploading(true);
    try {
      let result;
      if (tab === "images") {
        result = await uploadImages(imageFiles, "high", reconstructionMode);
      } else {
        result = await uploadVideo(videoFile, "high", reconstructionMode, density);
      }
      setTaskId(result.task.id);
      onTaskCreated?.(result.task);
    } catch (err) {
      setUploadError(err.message || "上传失败，请检查后端是否运行");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-panel">
      {/* ── Mode Selector ──────────────────────── */}
      <ModeSelector />

      {/* ── Input Tabs ─────────────────────────── */}
      <div className="glass-card upload-card">
        <div className="input-tabs">
          <button
            className={`tab-btn${tab === "images" ? " active" : ""}`}
            onClick={() => setTab("images")}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
            上传图片
          </button>
          <button
            className={`tab-btn${tab === "video" ? " active" : ""}`}
            onClick={() => setTab("video")}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="23 7 16 12 23 17 23 7"/>
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
            上传视频
          </button>
        </div>

        {/* ── Images Tab ────────────────────────── */}
        {tab === "images" && (
          <div className="upload-images-section">
            <FileDropZone
              multiple
              accept={ACCEPT_IMAGES}
              onFiles={handleImageFiles}
              icon={
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <polyline points="21 15 16 10 5 21"/>
                </svg>
              }
              label="拖拽图片到此处"
              hint="支持 JPG / PNG / TIFF / BMP"
            />

            {imageFiles.length > 0 && (
              <>
                <div className="file-info">
                  <span>图片: {imageFiles.length}</span>
                  <span>总大小: {totalSize}</span>
                  <button className="file-clear" onClick={handleClearImages}>
                    清空
                  </button>
                </div>
                <div className="file-grid">
                  {imageFiles.map((f, i) => (
                    <div key={`${f.name}-${i}`} className="file-item">
                      <img
                        src={URL.createObjectURL(f)}
                        alt={f.name}
                        className="file-thumb"
                      />
                      <button
                        className="file-remove"
                        onClick={() => handleRemoveImage(i)}
                        title="删除"
                      >
                        ✕
                      </button>
                      <span className="file-name">{f.name}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* ── Video Tab ─────────────────────────── */}
        {tab === "video" && (
          <div className="upload-video-section">
            {!videoFile ? (
              <FileDropZone
                accept={ACCEPT_VIDEO}
                onFiles={handleVideoFile}
                icon={
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="23 7 16 12 23 17 23 7"/>
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                  </svg>
                }
                label="拖拽视频文件到此处"
                hint="支持 MP4 / MOV / AVI / MKV / WebM"
              />
            ) : (
              <div className="video-preview-section">
                <video
                  src={URL.createObjectURL(videoFile)}
                  controls
                  className="video-preview"
                />
                <div className="file-info">
                  <span>{videoFile.name}</span>
                  <span>{totalSize}</span>
                  <button className="file-clear" onClick={handleClearVideo}>
                    更换
                  </button>
                </div>

                <div className="density-options">
                  <p className="density-label">抽帧密度</p>
                  <div className="density-btns">
                    {[15, 30, 60].map((d) => (
                      <button
                        key={d}
                        className={`density-btn${density === d ? " active" : ""}`}
                        onClick={() => setDensity(d)}
                      >
                        {densityLabels[d]}
                        <span className="density-num">{d}帧</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Submit ─────────────────────────────── */}
        <button
          className="btn-primary upload-submit"
          onClick={handleSubmit}
          disabled={uploading}
        >
          {uploading ? (
            <>
              <span className="spinner-sm" />
              正在上传...
            </>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              开始重建
            </>
          )}
        </button>

        {uploadError && (
          <div className="upload-error">{uploadError}</div>
        )}
      </div>

      {/* ── Advanced Settings ──────────────────── */}
      <AdvancedSettings />
    </div>
  );
}
