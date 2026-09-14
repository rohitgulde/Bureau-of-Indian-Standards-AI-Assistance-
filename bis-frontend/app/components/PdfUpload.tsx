"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle, ChevronDown, ChevronUp, Database } from "lucide-react";
import { useTranslation } from "react-i18next";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface FileItem {
  file: File;
  id: string;
}

type UploadState = "idle" | "uploading" | "done" | "error";

export default function PdfUpload() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [log, setLog] = useState<string[]>([]);
  const [dbVectors, setDbVectors] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);

  // Fetch initial DB status
  useEffect(() => {
    if (!open) return;
    fetch(`${API}/api/ingest/status`)
      .then((r) => r.json())
      .then((d) => setDbVectors(d.total_vectors ?? null))
      .catch(() => {});
  }, [open]);

  // Auto-scroll log to bottom
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [log]);

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const pdfs = Array.from(incoming).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    setFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.file.name));
      const newItems = pdfs
        .filter((f) => !existingNames.has(f.name))
        .map((f) => ({ file: f, id: `${f.name}-${f.size}` }));
      return [...prev, ...newItems];
    });
  }, []);

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(e.target.files);
    e.target.value = "";
  };

  const handleUpload = async () => {
    if (!files.length || uploadState === "uploading") return;

    setUploadState("uploading");
    setLog(["Connecting to backend…"]);

    const form = new FormData();
    files.forEach((f) => form.append("files", f.file));

    try {
      const res = await fetch(`${API}/api/ingest/upload`, {
        method: "POST",
        body: form,
      });

      if (!res.ok || !res.body) {
        const err = await res.text();
        setLog((l) => [...l, `❌ Server error: ${err}`]);
        setUploadState("error");
        return;
      }

      // Stream SSE
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: streamDone } = await reader.read();
        done = streamDone;
        if (!value) continue;

        const text = decoder.decode(value);
        const lines = text.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const msg = line.slice(6).trim();
          if (!msg) continue;
          if (msg === "DONE") {
            setUploadState("done");
            // Refresh DB count
            fetch(`${API}/api/ingest/status`)
              .then((r) => r.json())
              .then((d) => setDbVectors(d.total_vectors ?? null))
              .catch(() => {});
          } else {
            setLog((l) => [...l, msg]);
          }
        }
      }

      if (uploadState !== "done") setUploadState("done");
    } catch (err) {
      setLog((l) => [...l, `❌ Network error: ${err}`]);
      setUploadState("error");
    }
  };

  const reset = () => {
    setFiles([]);
    setLog([]);
    setUploadState("idle");
  };

  const fmt = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
      {/* ── Header / Toggle ──────────────────────────────────────────── */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-muted/40 transition-colors group"
        id="pdf-upload-toggle"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <Upload size={14} className="text-primary" />
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-foreground leading-none">{t("upload_standards_title")}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {dbVectors !== null ? `${dbVectors.toLocaleString()} vectors in DB` : t("upload_standards_desc")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {dbVectors !== null && dbVectors > 0 && (
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-600 border border-green-500/20 font-medium">
              <Database size={9} />
              {dbVectors.toLocaleString()}
            </span>
          )}
          {open ? <ChevronUp size={15} className="text-muted-foreground" /> : <ChevronDown size={15} className="text-muted-foreground" />}
        </div>
      </button>

      {/* ── Expandable body ──────────────────────────────────────────── */}
      {open && (
        <div className="border-t border-border px-5 py-4 space-y-4">

          {/* Drop zone */}
          {uploadState === "idle" && (
            <>
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`
                  relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer
                  transition-all duration-200 group
                  ${dragging
                    ? "border-primary bg-primary/8 scale-[1.01]"
                    : "border-border hover:border-primary/50 hover:bg-muted/30"
                  }
                `}
                id="pdf-drop-zone"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  multiple
                  onChange={onInputChange}
                  className="hidden"
                  id="pdf-file-input"
                />
                <div className={`w-12 h-12 rounded-xl mx-auto mb-3 flex items-center justify-center transition-colors
                  ${dragging ? "bg-primary/15" : "bg-muted/60 group-hover:bg-primary/10"}`}>
                  <Upload size={22} className={`transition-colors ${dragging ? "text-primary" : "text-muted-foreground group-hover:text-primary"}`} />
                </div>
                <p className="text-sm font-medium text-foreground">
                  {dragging ? "Drop PDFs here" : t("drag_drop")}
                </p>
                <p className="text-[11px] text-muted-foreground mt-1">
                  or <span className="text-primary font-medium">{t("click_to_browse")}</span> · {t("multiple_files_supported")}
                </p>
              </div>

              {/* File list */}
              {files.length > 0 && (
                <ul className="space-y-1.5">
                  {files.map((f) => (
                    <li key={f.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/40 border border-border group">
                      <FileText size={14} className="text-primary flex-shrink-0" />
                      <span className="text-xs text-foreground truncate flex-1 font-medium">{f.file.name}</span>
                      <span className="text-[10px] text-muted-foreground flex-shrink-0">{fmt(f.file.size)}</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); removeFile(f.id); }}
                        className="ml-1 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        id={`remove-file-${f.id}`}
                      >
                        <X size={13} />
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {/* Upload button */}
              <button
                onClick={handleUpload}
                disabled={files.length === 0}
                className={`
                  w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-200
                  flex items-center justify-center gap-2
                  ${files.length > 0
                    ? "bg-primary text-primary-foreground hover:opacity-90 shadow-sm hover:shadow-md"
                    : "bg-muted text-muted-foreground cursor-not-allowed opacity-60"
                  }
                `}
                id="start-ingest-button"
              >
                <Upload size={15} />
                {files.length === 0
                  ? t("select_pdfs_first")
                  : `Ingest ${files.length} PDF${files.length > 1 ? "s" : ""}`
                }
              </button>
            </>
          )}

          {/* Progress log */}
          {(uploadState === "uploading" || uploadState === "done" || uploadState === "error") && (
            <div className="space-y-3">
              {/* Status badge */}
              <div className="flex items-center gap-2">
                {uploadState === "uploading" && (
                  <>
                    <Loader2 size={14} className="text-primary animate-spin" />
                    <span className="text-xs font-medium text-primary">Ingesting…</span>
                  </>
                )}
                {uploadState === "done" && (
                  <>
                    <CheckCircle2 size={14} className="text-green-500" />
                    <span className="text-xs font-medium text-green-600">Ingestion complete!</span>
                  </>
                )}
                {uploadState === "error" && (
                  <>
                    <AlertCircle size={14} className="text-destructive" />
                    <span className="text-xs font-medium text-destructive">Ingestion failed</span>
                  </>
                )}
              </div>

              {/* Terminal log */}
              <div
                ref={logRef}
                className="bg-sidebar rounded-xl p-3.5 h-52 overflow-y-auto font-mono text-[11px] leading-relaxed space-y-0.5 border border-sidebar-border"
                id="ingest-log"
              >
                {log.map((line, i) => (
                  <div key={i} className={`
                    ${line.startsWith("✅") || line.startsWith("✔") ? "text-green-400" :
                      line.startsWith("❌") ? "text-red-400" :
                      line.startsWith("⚠️") ? "text-yellow-400" :
                      line.startsWith("🚀") || line.startsWith("📄") ? "text-blue-300" :
                      line.startsWith("🔢") || line.startsWith("💾") ? "text-purple-300" :
                      line.startsWith("─") ? "text-sidebar-border" :
                      "text-sidebar-foreground/80"
                    }
                  `}>
                    {line || "\u00a0"}
                  </div>
                ))}
                {uploadState === "uploading" && (
                  <div className="text-primary animate-pulse">▋</div>
                )}
              </div>

              {/* Reset button (shown after completion) */}
              {(uploadState === "done" || uploadState === "error") && (
                <button
                  onClick={reset}
                  className="w-full py-2 rounded-xl text-xs font-semibold border border-border hover:bg-muted/50 text-foreground transition-colors"
                  id="reset-upload-button"
                >
                  Upload more PDFs
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
