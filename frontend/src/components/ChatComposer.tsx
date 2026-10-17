"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowUp,
  FileText,
  GitCompare,
  Loader2,
  Paperclip,
  Search,
  ShieldCheck,
  Square,
  UploadCloud,
  X,
} from "lucide-react";
import { RetrievalMode } from "@/types/api";

interface ChatComposerProps {
  onSendMessage: (content: string) => Promise<void>;
  onStopGeneration: () => void;
  onUploadFiles: (files: File[]) => Promise<void>;
  isStreaming: boolean;
  isUploading: boolean;
  retrievalMode: RetrievalMode;
  onChangeRetrievalMode: (mode: RetrievalMode) => void;
  activeModelName: string;
  activeCollectionName: string;
  documentCount: number;
  errorMessage: string | null;
  onClearError: () => void;
}

const RETRIEVAL_MODES: Array<{
  id: RetrievalMode;
  label: string;
  shortLabel: string;
  description: string;
  icon: React.ReactNode;
}> = [
  {
    id: "corrective_rag",
    label: "Corrective RAG (CRAG)",
    shortLabel: "Corrective RAG",
    description: "Grades retrieval quality & rewrites weak searches automatically",
    icon: <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />,
  },
  {
    id: "document_search",
    label: "Document Search",
    shortLabel: "Doc Search",
    description: "Fast hybrid vector + keyword retrieval across active files",
    icon: <Search className="w-3.5 h-3.5 text-blue-500" />,
  },
  {
    id: "compare_documents",
    label: "Compare Documents",
    shortLabel: "Compare Docs",
    description: "Diversifies retrieval across files to compare claims & metrics",
    icon: <GitCompare className="w-3.5 h-3.5 text-purple-500" />,
  },
];

export default function ChatComposer({
  onSendMessage,
  onStopGeneration,
  onUploadFiles,
  isStreaming,
  isUploading,
  retrievalMode,
  onChangeRetrievalMode,
  activeModelName,
  activeCollectionName,
  documentCount,
  errorMessage,
  onClearError,
}: ChatComposerProps) {
  const [input, setInput] = useState("");
  const [stagedFiles, setStagedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea within max height (200px)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isStreaming || isUploading) return;

    // Upload any staged files first before sending message
    if (stagedFiles.length > 0) {
      const filesToUpload = [...stagedFiles];
      setStagedFiles([]);
      await onUploadFiles(filesToUpload);
    }

    const trimmed = input.trim();
    if (!trimmed) return;
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    await onSendMessage(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = Array.from(e.target.files);
      setStagedFiles((prev) => [...prev, ...selected]);
      e.target.value = "";
    }
  };

  const handleUploadStagedNow = async () => {
    if (stagedFiles.length === 0 || isUploading) return;
    const filesToUpload = [...stagedFiles];
    setStagedFiles([]);
    await onUploadFiles(filesToUpload);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const dropped = Array.from(e.dataTransfer.files);
      setStagedFiles((prev) => [...prev, ...dropped]);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-3 sm:px-4 pb-3 pt-1">
      {/* Error banner */}
      {errorMessage && (
        <div className="mb-2 flex items-center justify-between gap-2 px-3.5 py-2 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800/70 text-rose-700 dark:text-rose-300 text-xs animate-in fade-in duration-150">
          <div className="flex items-center gap-2 min-w-0">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span className="truncate">{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={onClearError}
            className="p-0.5 rounded hover:bg-rose-200/50 dark:hover:bg-rose-900/50"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Rounded Composer Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-3xl bg-zinc-100/90 dark:bg-zinc-900/95 border transition-all shadow-sm ${
          isDragging
            ? "border-blue-500 ring-2 ring-blue-500/20 bg-blue-50/40 dark:bg-blue-950/20"
            : "border-zinc-200/90 dark:border-zinc-800 focus-within:border-zinc-300 dark:focus-within:border-zinc-700 focus-within:shadow-md"
        }`}
      >
        {/* Drag overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-20 rounded-3xl bg-blue-500/10 backdrop-blur-[1px] flex items-center justify-center pointer-events-none">
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white dark:bg-zinc-900 shadow-md text-xs font-semibold text-blue-600 dark:text-blue-400">
              <UploadCloud className="w-4 h-4" />
              Drop documents (PDF, DOCX, XLSX, CSV, MD, TXT) to attach
            </div>
          </div>
        )}

        {/* Staged files bar */}
        {(stagedFiles.length > 0 || isUploading) && (
          <div className="flex flex-wrap items-center gap-2 px-4 pt-3 pb-1 border-b border-zinc-200/60 dark:border-zinc-800/60">
            {stagedFiles.map((file, idx) => (
              <div
                key={`${file.name}-${idx}`}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-700 dark:text-zinc-200 shadow-2xs"
              >
                <FileText className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                <span className="truncate max-w-[150px]">{file.name}</span>
                <span className="text-[10px] text-zinc-400">
                  ({Math.max(1, Math.round(file.size / 1024))} KB)
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setStagedFiles((prev) => prev.filter((_, i) => i !== idx))
                  }
                  className="p-0.5 text-zinc-400 hover:text-rose-500 rounded"
                  title="Remove file"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}

            {stagedFiles.length > 0 && !isUploading && (
              <button
                type="button"
                onClick={handleUploadStagedNow}
                className="px-2.5 py-1 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
              >
                Index {stagedFiles.length} {stagedFiles.length === 1 ? "file" : "files"} now
              </button>
            )}

            {isUploading && (
              <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400 font-medium py-1">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Parsing & indexing documents into {activeCollectionName}...</span>
              </div>
            )}
          </div>
        )}

        {/* Multiline Textarea */}
        <div className="px-4 pt-3 pb-1">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isUploading}
            placeholder={
              documentCount > 0
                ? `Ask anything about your ${documentCount} indexed ${
                    documentCount === 1 ? "document" : "documents"
                  } in ${activeCollectionName}...`
                : "Upload documents or ask a question (Enter to send, Shift+Enter for new line)..."
            }
            aria-label="Message input"
            className="w-full resize-none bg-transparent text-sm sm:text-[15px] text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none max-h-[200px] leading-relaxed"
          />
        </div>

        {/* Bottom Toolbar: Attach, Retrieval Mode Pills, Active Model Indicator, Send/Stop */}
        <div className="flex items-center justify-between gap-2 px-3 pb-2.5 pt-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.png,.jpg,.jpeg,.webp"
              onChange={handleFileChange}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || isStreaming}
              title="Attach files (PDF, DOCX, XLSX, CSV, TXT, MD)"
              aria-label="Attach files"
              className="inline-flex items-center gap-1.5 p-2 rounded-full text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-200/70 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            {/* Retrieval Mode Selector Pills */}
            <div
              role="radiogroup"
              aria-label="Retrieval Mode"
              className="inline-flex items-center p-0.5 rounded-full bg-zinc-200/70 dark:bg-zinc-800/90 border border-zinc-300/40 dark:border-zinc-700/50"
            >
              {RETRIEVAL_MODES.map((m) => {
                const active = retrievalMode === m.id;
                return (
                  <button
                    key={m.id}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => onChangeRetrievalMode(m.id)}
                    title={`${m.label}: ${m.description}`}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                      active
                        ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-2xs"
                        : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
                    }`}
                  >
                    {m.icon}
                    <span className="hidden sm:inline">{m.shortLabel}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="hidden md:inline-block text-[11px] text-zinc-400 dark:text-zinc-500 truncate max-w-[140px]">
              {activeModelName}
            </span>

            {isStreaming ? (
              <button
                type="button"
                onClick={onStopGeneration}
                title="Stop generating response"
                aria-label="Stop generation"
                className=" inline-flex items-center justify-center w-8 h-8 rounded-full bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:opacity-90 transition-opacity shadow-xs"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleSubmit()}
                disabled={(!input.trim() && stagedFiles.length === 0) || isUploading}
                title="Send message (Enter)"
                aria-label="Send message"
                className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-xs"
              >
                <ArrowUp className="w-4 h-4 stroke-[2.5]" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Subtle footer caption */}
      <div className="mt-1.5 flex items-center justify-center gap-2 text-[11px] text-zinc-400 dark:text-zinc-500 text-center">
        <span>
          Grounded in <strong className="font-medium text-zinc-500 dark:text-zinc-400">{activeCollectionName}</strong> ({documentCount} {documentCount === 1 ? "file" : "files"})
        </span>
        <span>•</span>
        <span>Click any [Source N] citation to inspect original passage</span>
      </div>
    </div>
  );
}
