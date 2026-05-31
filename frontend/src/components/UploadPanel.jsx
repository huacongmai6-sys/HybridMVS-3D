import { useState, useRef } from "react";
import { uploadImages } from "../api";

const STAGE_LABELS = {
  sfm_extract_features: "Extracting features...",
  sfm_complete: "Sparse reconstruction complete",
  convert: "Converting data format...",
  mvs_depth: "Estimating depth maps...",
  mvs_complete: "Depth estimation complete",
  fusion: "Fusing point cloud...",
  complete: "Reconstruction complete",
  error: "Error occurred",
};

export default function UploadPanel({ onTaskCreated }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files).filter(
      (f) => f.type.startsWith("image/")
    );
    setFiles((prev) => [...prev, ...dropped]);
  };

  const handleSelect = (e) => {
    const selected = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...selected]);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    try {
      const result = await uploadImages(files);
      onTaskCreated?.(result.task);
      setFiles([]);
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-panel">
      <h2>上传图片</h2>
      <p>选择同一场景的多视角图片进行三维重建</p>

      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <span className="drop-icon">+</span>
        <p>拖拽图片到此处，或点击选择文件</p>
        <p className="hint">支持格式：JPG、PNG、TIFF、BMP</p>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*"
        style={{ display: "none" }}
        onChange={handleSelect}
      />

      {files.length > 0 && (
        <div className="file-list">
          <h4>
            {files.length} 张图片已选择
          </h4>
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
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? "上传中..." : "开始重建"}
          </button>
        </div>
      )}
    </div>
  );
}
