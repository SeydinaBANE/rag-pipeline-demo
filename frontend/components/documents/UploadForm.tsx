"use client";

import { CheckCircle, Upload, XCircle } from "lucide-react";
import { type DragEvent, useRef, useState } from "react";

import { ingestFile } from "@/lib/api";
import type { IngestResponse } from "@/lib/types";

type Status = "idle" | "uploading" | "success" | "error";

interface UploadResult {
  file: string;
  response?: IngestResponse;
  error?: string;
}

export function UploadForm() {
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<UploadResult[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setStatus("uploading");
    const newResults: UploadResult[] = [];

    for (const file of Array.from(files)) {
      try {
        const response = await ingestFile(file);
        newResults.push({ file: file.name, response });
      } catch (err) {
        newResults.push({
          file: file.name,
          error: err instanceof Error ? err.message : "Upload failed",
        });
      }
    }

    setResults((prev) => [...newResults, ...prev]);
    setStatus(newResults.some((r) => r.error) ? "error" : "success");
    setTimeout(() => setStatus("idle"), 2000);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    void processFiles(e.dataTransfer.files);
  };

  return (
    <div className="space-y-4">
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          dragOver
            ? "border-blue-400 bg-blue-50"
            : "border-gray-300 hover:border-blue-300 hover:bg-gray-50"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.docx"
          className="hidden"
          onChange={(e) => void processFiles(e.target.files)}
        />
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-3" />
        <p className="text-sm font-medium text-gray-700">
          {status === "uploading" ? "Uploading…" : "Drop files or click to browse"}
        </p>
        <p className="text-xs text-gray-400 mt-1">PDF, TXT, MD, DOCX</p>
      </div>

      {results.length > 0 && (
        <ul className="space-y-2">
          {results.map((r, i) => (
            <li
              key={i}
              className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-2.5 text-sm"
            >
              {r.error ? (
                <XCircle className="w-4 h-4 text-red-500 shrink-0" />
              ) : (
                <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
              )}
              <span className="flex-1 truncate text-gray-700">{r.file}</span>
              {r.response && (
                <span className="text-gray-400 text-xs">
                  {r.response.document_count} chunks · job {r.response.job_id.slice(0, 8)}
                </span>
              )}
              {r.error && (
                <span className="text-red-500 text-xs">{r.error}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
