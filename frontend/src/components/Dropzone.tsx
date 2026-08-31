import { useCallback, useRef, useState } from "react";

const ACCEPTED_TYPES = [".pdf", ".docx"];
const ACCEPTED_MIME = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

interface DropzoneProps {
  file: File | null;
  onFileSelected: (file: File | null) => void;
  error: string | null;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function Dropzone({ file, onFileSelected, error }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const candidate = files?.[0];
      if (!candidate) return;
      const extOk = ACCEPTED_TYPES.some((ext) => candidate.name.toLowerCase().endsWith(ext));
      const mimeOk = ACCEPTED_MIME.includes(candidate.type);
      if (!extOk && !mimeOk) {
        onFileSelected(null);
        return;
      }
      onFileSelected(candidate);
    },
    [onFileSelected]
  );

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-14 text-center transition-colors ${
          isDragging
            ? "border-[var(--color-accent)] bg-[var(--color-accent-tint)]"
            : "border-[var(--color-line-strong)] bg-[var(--color-surface)] hover:border-[var(--color-accent-soft)]"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <svg
          aria-hidden
          viewBox="0 0 24 24"
          className="mb-4 h-9 w-9 stroke-[var(--color-ink-faint)] fill-none stroke-[1.4]"
        >
          <path d="M12 3v12m0-12l-4 4m4-4l4 4M5 17v2a2 2 0 002 2h10a2 2 0 002-2v-2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>

        {file ? (
          <div>
            <p className="font-mono text-sm font-medium text-[var(--color-ink)]">{file.name}</p>
            <p className="mt-1 text-xs text-[var(--color-ink-faint)]">{formatBytes(file.size)} · click to replace</p>
          </div>
        ) : (
          <div>
            <p className="text-sm font-medium text-[var(--color-ink)]">
              Drop a document here, or <span className="text-[var(--color-accent)] underline">browse</span>
            </p>
            <p className="mt-1 text-xs text-[var(--color-ink-faint)]">PDF or DOCX, loan agreements, policies, and KYC documents</p>
          </div>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-[var(--color-risk-bad)]">{error}</p>}
    </div>
  );
}
