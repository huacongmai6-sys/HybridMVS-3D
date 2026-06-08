import { useRef, useState } from "react";

/**
 * FileDropZone — Reusable drag-and-drop file input.
 *
 * @param {object} props
 * @param {boolean} props.multiple - allow multiple files
 * @param {string} props.accept - MIME types (e.g. "image/*")
 * @param {function} props.onFiles - called with selected File[]
 * @param {ReactNode} props.icon - icon element
 * @param {string} props.label - main instruction text
 * @param {string} props.hint - secondary hint text
 */
export default function FileDropZone({
  multiple = false,
  accept = "image/*",
  onFiles,
  icon,
  label = "拖拽文件到此处",
  hint = "或点击选择文件",
}) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragIn = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragOut = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      const valid = accept
        ? files.filter((f) =>
            accept.split(",").some((a) => {
              const pattern = a.trim().replace("*", ".*");
              return new RegExp(pattern, "i").test(f.type) ||
                     f.name.toLowerCase().endsWith(pattern.replace(".*", ""));
            })
          )
        : files;

      if (valid.length > 0) onFiles(multiple ? valid : [valid[0]]);
    }
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) onFiles(files);
    /* Reset so re-selecting the same file works */
    e.target.value = "";
  };

  return (
    <div
      className={`drop-zone${dragOver ? " drag-over" : ""}`}
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") handleClick();
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
      {icon && <div className="drop-zone-icon">{icon}</div>}
      <p className="drop-zone-label">{dragOver ? "松开放置文件" : label}</p>
      <p className="drop-zone-hint">{hint}</p>
    </div>
  );
}
