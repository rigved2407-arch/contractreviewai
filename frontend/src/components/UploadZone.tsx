"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, Loader2, CheckCircle } from "lucide-react";
import { api } from "@/lib/api";
import type { Contract } from "@/types";

interface Props {
  onUploaded: (contract: Contract) => void;
}

export default function UploadZone({ onUploaded }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.match(/\.(pdf|docx?)$/i)) {
        setResult({ ok: false, msg: "Only PDF and DOCX files are supported" });
        return;
      }
      setUploading(true);
      setResult(null);
      try {
        const contract = await api.uploadContract(file);
        setResult({ ok: true, msg: `${file.name} uploaded successfully` });
        onUploaded(contract);
      } catch (err: any) {
        setResult({ ok: false, msg: err.message || "Upload failed" });
      } finally {
        setUploading(false);
      }
    },
    [onUploaded]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
        dragOver
          ? "border-indigo-500 bg-indigo-50"
          : "border-gray-300 hover:border-indigo-400 hover:bg-gray-50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />

      {uploading ? (
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
          <p className="text-gray-600">Uploading and parsing...</p>
        </div>
      ) : result?.ok ? (
        <div className="flex flex-col items-center gap-3">
          <CheckCircle className="w-10 h-10 text-green-600" />
          <p className="text-green-700 font-medium">{result.msg}</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          {result && !result.ok && (
            <p className="text-red-600 text-sm mb-2">{result.msg}</p>
          )}
          <Upload className="w-10 h-10 text-gray-400" />
          <div>
            <p className="text-gray-700 font-medium">
              Drop a contract here, or click to browse
            </p>
            <p className="text-gray-500 text-sm mt-1">
              PDF, DOCX up to 50MB
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
