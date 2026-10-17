"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  FileSpreadsheet,
  FileText,
  FolderPlus,
  Layers,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import {
  ChunkDetailResponse,
  Citation,
  Collection,
  DocumentItem,
} from "@/types/api";
import { fetchChunkDetails } from "@/lib/api";

interface DocumentContextPanelProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: "library" | "inspector";
  onTabChange: (tab: "library" | "inspector") => void;
  collections: Collection[];
  activeCollectionId: string;
  onSelectCollection: (colId: string) => void;
  onCreateCollection: (name: string, description: string) => Promise<void>;
  onDeleteCollection: (colId: string) => Promise<void>;
  documents: DocumentItem[];
  isUploading: boolean;
  onUploadFiles: (files: File[]) => Promise<void>;
  onReindexDocument: (docId: string) => Promise<void>;
  onDeleteDocument: (docId: string) => Promise<void>;
  selectedCitation: Citation | null;
}

const SUPPORTED_FORMATS = ["PDF", "DOCX", "XLSX", "CSV", "MD", "TXT", "OCR Images"];

export default function DocumentContextPanel({
  isOpen,
  onClose,
  activeTab,
  onTabChange,
  collections,
  activeCollectionId,
  onSelectCollection,
  onCreateCollection,
  onDeleteCollection,
  documents,
  isUploading,
  onUploadFiles,
  onReindexDocument,
  onDeleteDocument,
  selectedCitation,
}: DocumentContextPanelProps) {
  const [showNewCollection, setShowNewCollection] = useState(false);
  const [newColName, setNewColName] = useState("");
  const [newColDesc, setNewColDesc] = useState("");
  const [creatingCol, setCreatingCol] = useState(false);
  const [reindexingDocId, setReindexingDocId] = useState<string | null>(null);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Citation / Chunk Inspector state
  const [chunkDetail, setChunkDetail] = useState<ChunkDetailResponse | null>(null);
  const [loadingChunk, setLoadingChunk] = useState(false);
  const [chunkSearch, setChunkSearch] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const highlightedChunkRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedCitation && selectedCitation.chunk_id) {
      setLoadingChunk(true);
      fetchChunkDetails(selectedCitation.chunk_id)
        .then((res) => {
          setChunkDetail(res);
          setTimeout(() => {
            highlightedChunkRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "center",
            });
          }, 120);
        })
        .catch(() => {
          setChunkDetail(null);
        })
        .finally(() => {
          setLoadingChunk(false);
        });
    }
  }, [selectedCitation]);

  if (!isOpen) return null;

  const activeCollection =
    collections.find((c) => c.id === activeCollectionId) || collections[0];

  const handleCreateColSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newColName.trim()) return;
    setCreatingCol(true);
    try {
      await onCreateCollection(newColName.trim(), newColDesc.trim());
      setNewColName("");
      setNewColDesc("");
      setShowNewCollection(false);
    } finally {
      setCreatingCol(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      e.target.value = "";
      await onUploadFiles(files);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      await onUploadFiles(files);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const filteredDocChunks =
    chunkDetail?.document_chunks?.filter((ch) =>
      chunkSearch.trim()
        ? ch.text.toLowerCase().includes(chunkSearch.toLowerCase()) ||
          (ch.heading && ch.heading.toLowerCase().includes(chunkSearch.toLowerCase()))
        : true
    ) || [];

  return (
    <>
      {/* Mobile / Tablet Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/30 backdrop-blur-[1px] z-30 xl:hidden"
      />

      <aside
        aria-label="Document Context and Citation Inspector"
        className="fixed xl:static inset-y-0 right-0 z-40 w-[340px] sm:w-[390px] flex flex-col bg-zinc-50 dark:bg-zinc-950 border-l border-zinc-200/80 dark:border-zinc-800/80 shadow-xl xl:shadow-none animate-in slide-in-from-right duration-200"
      >
        {/* Top Header + Tabs */}
        <div className="px-4 pt-3 pb-2 border-b border-zinc-200/80 dark:border-zinc-800/80 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-500" />
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Document Workspace
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              title="Close panel"
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 p-0.5 rounded-xl bg-zinc-200/70 dark:bg-zinc-900 border border-zinc-200/60 dark:border-zinc-800">
            <button
              type="button"
              onClick={() => onTabChange("library")}
              className={`py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === "library"
                  ? "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-2xs"
                  : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200"
              }`}
            >
              Files ({documents.length})
            </button>
            <button
              type="button"
              onClick={() => onTabChange("inspector")}
              className={`py-1.5 text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                activeTab === "inspector"
                  ? "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-2xs"
                  : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200"
              }`}
            >
              <BookOpen className="w-3.5 h-3.5 text-blue-500" />
              <span>Source Inspector</span>
            </button>
          </div>
        </div>

        {/* TAB 1: DOCUMENT LIBRARY & MULTI-FILE UPLOAD */}
        {activeTab === "library" ? (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Active Collection Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  Active Collection
                </label>
                <button
                  type="button"
                  onClick={() => setShowNewCollection((prev) => !prev)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
                >
                  <FolderPlus className="w-3.5 h-3.5" />
                  <span>New Collection</span>
                </button>
              </div>

              <div className="flex items-center gap-1.5">
                <select
                  value={activeCollectionId}
                  onChange={(e) => onSelectCollection(e.target.value)}
                  className="flex-1 px-3 py-2 text-xs font-medium rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                >
                  {collections.map((col) => (
                    <option key={col.id} value={col.id}>
                      {col.name} ({col.document_count ?? 0} files)
                    </option>
                  ))}
                </select>

                {activeCollectionId !== "default" && (
                  <button
                    type="button"
                    onClick={() => onDeleteCollection(activeCollectionId)}
                    title="Delete collection and its files"
                    className="p-2 rounded-xl text-zinc-400 hover:text-rose-600 hover:bg-rose-500/10 border border-zinc-200 dark:border-zinc-800"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              {showNewCollection && (
                <form
                  onSubmit={handleCreateColSubmit}
                  className="p-3 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-2 animate-in fade-in duration-150"
                >
                  <input
                    type="text"
                    required
                    value={newColName}
                    onChange={(e) => setNewColName(e.target.value)}
                    placeholder="Collection name (e.g., Q4 Legal Contracts)"
                    className="w-full px-2.5 py-1.5 text-xs rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none"
                  />
                  <input
                    type="text"
                    value={newColDesc}
                    onChange={(e) => setNewColDesc(e.target.value)}
                    placeholder="Optional description..."
                    className="w-full px-2.5 py-1.5 text-xs rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none"
                  />
                  <div className="flex justify-end gap-1.5">
                    <button
                      type="button"
                      onClick={() => setShowNewCollection(false)}
                      className="px-2.5 py-1 text-xs rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={creatingCol}
                      className="px-3 py-1 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50"
                    >
                      {creatingCol ? "Creating..." : "Create"}
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* Drag and Drop Upload Box */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => !isUploading && fileInputRef.current?.click()}
              className={`p-4 rounded-2xl border-2 border-dashed text-center cursor-pointer transition-all ${
                isDragging
                  ? "border-blue-500 bg-blue-50/50 dark:bg-blue-950/30"
                  : "border-zinc-300 dark:border-zinc-800 hover:border-blue-400 dark:hover:border-zinc-700 bg-white/60 dark:bg-zinc-900/50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.png,.jpg,.jpeg,.webp"
                onChange={handleFileSelect}
                className="hidden"
              />
              {isUploading ? (
                <div className="py-2 flex flex-col items-center gap-2">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                  <p className="text-xs font-medium text-zinc-700 dark:text-zinc-200">
                    Parsing & building hybrid vector index...
                  </p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center mx-auto">
                    <UploadCloud className="w-5 h-5" />
                  </div>
                  <p className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Click or drag files to upload into {activeCollection?.name}
                  </p>
                  <div className="flex flex-wrap justify-center gap-1 pt-1">
                    {SUPPORTED_FORMATS.map((fmt) => (
                      <span
                        key={fmt}
                        className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400"
                      >
                        {fmt}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Uploaded Document List */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  Indexed Files ({documents.length})
                </p>
              </div>

              {documents.length === 0 ? (
                <div className="py-8 text-center rounded-2xl bg-white/50 dark:bg-zinc-900/40 border border-zinc-200/60 dark:border-zinc-800/60 p-4">
                  <FileText className="w-7 h-7 text-zinc-300 dark:text-zinc-700 mx-auto mb-1.5" />
                  <p className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
                    No documents in this collection
                  </p>
                  <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-0.5">
                    Uploaded files are chunked with page, heading, and table provenance.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map((doc) => {
                    const isExcelOrCsv =
                      doc.file_type === "XLSX" || doc.file_type === "CSV";
                    const isReindexing = reindexingDocId === doc.id;
                    const isDeleting = deletingDocId === doc.id;

                    return (
                      <div
                        key={doc.id}
                        className="p-3 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/90 shadow-2xs space-y-2"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-start gap-2.5 min-w-0">
                            {isExcelOrCsv ? (
                              <FileSpreadsheet className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                            ) : (
                              <FileText className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                            )}
                            <div className="min-w-0">
                              <p
                                className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 truncate"
                                title={doc.filename}
                              >
                                {doc.filename}
                              </p>
                              <div className="flex items-center flex-wrap gap-1.5 text-[11px] text-zinc-400 dark:text-zinc-500 mt-0.5">
                                <span>{doc.file_type}</span>
                                <span>•</span>
                                <span>{formatBytes(doc.file_size)}</span>
                                <span>•</span>
                                <span>{doc.chunk_count} chunks</span>
                              </div>
                            </div>
                          </div>

                          {/* Status Badge */}
                          {doc.status === "indexed" ? (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 shrink-0">
                              <CheckCircle2 className="w-3 h-3" />
                              Indexed
                            </span>
                          ) : doc.status === "processing" ? (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 shrink-0">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Indexing
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-rose-500/10 text-rose-600 dark:text-rose-400 shrink-0">
                              <AlertCircle className="w-3 h-3" />
                              Error
                            </span>
                          )}
                        </div>

                        {doc.error_message && (
                          <p className="text-[11px] text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 px-2 py-1 rounded">
                            {doc.error_message}
                          </p>
                        )}

                        <div className="flex items-center justify-end gap-1.5 pt-1 border-t border-zinc-100 dark:border-zinc-800/60">
                          <button
                            type="button"
                            disabled={isReindexing}
                            onClick={async () => {
                              setReindexingDocId(doc.id);
                              try {
                                await onReindexDocument(doc.id);
                              } finally {
                                setReindexingDocId(null);
                              }
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                            title="Re-parse and re-index document"
                          >
                            <RefreshCw
                              className={`w-3 h-3 ${isReindexing ? "animate-spin" : ""}`}
                            />
                            <span>Re-index</span>
                          </button>

                          <button
                            type="button"
                            disabled={isDeleting}
                            onClick={async () => {
                              setDeletingDocId(doc.id);
                              try {
                                await onDeleteDocument(doc.id);
                              } finally {
                                setDeletingDocId(null);
                              }
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 transition-colors"
                            title="Delete document and purge chunks"
                          >
                            <Trash2 className="w-3 h-3" />
                            <span>{isDeleting ? "Removing..." : "Remove"}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* TAB 2: CITATION & SOURCE INSPECTOR */
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {!selectedCitation ? (
              <div className="py-12 text-center space-y-2 px-4">
                <BookOpen className="w-8 h-8 text-zinc-300 dark:text-zinc-700 mx-auto" />
                <p className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  No Citation Selected
                </p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  Click any <span className="font-mono text-blue-500">[Source N]</span> badge
                  inside an assistant response to inspect the exact cited document passage,
                  page number, heading, or spreadsheet rows.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Active Citation Header Card */}
                <div className="p-3.5 rounded-2xl bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200/80 dark:border-blue-800/70 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-600 text-white text-xs font-semibold">
                      Source {selectedCitation.citation_index}
                    </span>
                    <span className="text-[11px] font-medium text-blue-700 dark:text-blue-300">
                      Relevance: {(selectedCitation.score * 100).toFixed(1)}% (
                      {selectedCitation.relevance_grade})
                    </span>
                  </div>

                  <div>
                    <p className="text-xs font-bold text-zinc-900 dark:text-zinc-100 break-all">
                      {selectedCitation.filename}
                    </p>
                    <p className="text-[11px] text-zinc-600 dark:text-zinc-300 mt-0.5">
                      Location: <strong>{selectedCitation.location_label}</strong>
                      {selectedCitation.heading ? ` • Section: ${selectedCitation.heading}` : ""}
                      {selectedCitation.sheet_name
                        ? ` • Sheet: ${selectedCitation.sheet_name} (${selectedCitation.row_range})`
                        : ""}
                    </p>
                  </div>

                  <div className="p-2.5 rounded-xl bg-white dark:bg-zinc-900 border border-blue-200/60 dark:border-blue-900/50 text-xs text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap leading-relaxed max-h-[220px] overflow-y-auto">
                    {selectedCitation.excerpt}
                  </div>
                </div>

                {/* Full Document Chunks Navigation */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                      Document Context Chunks
                    </p>
                    {chunkDetail && (
                      <span className="text-[11px] text-zinc-400">
                        {chunkDetail.document_chunks.length} total chunks
                      </span>
                    )}
                  </div>

                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={chunkSearch}
                      onChange={(e) => setChunkSearch(e.target.value)}
                      placeholder="Filter passages in this document..."
                      className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 focus:outline-none"
                    />
                  </div>

                  {loadingChunk ? (
                    <div className="py-8 flex items-center justify-center gap-2 text-xs text-zinc-400">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                      <span>Loading full source context...</span>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {filteredDocChunks.map((ch) => {
                        const isCited = ch.id === selectedCitation.chunk_id;
                        return (
                          <div
                            key={ch.id}
                            ref={isCited ? highlightedChunkRef : null}
                            className={`p-3 rounded-xl border text-xs transition-all ${
                              isCited
                                ? "bg-amber-50/80 dark:bg-amber-950/30 border-amber-400 dark:border-amber-700 ring-1 ring-amber-400/30"
                                : "bg-white dark:bg-zinc-900 border-zinc-200/70 dark:border-zinc-800/80"
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2 mb-1 text-[11px] text-zinc-400 dark:text-zinc-500">
                              <span className="font-semibold text-zinc-600 dark:text-zinc-300">
                                Chunk #{ch.chunk_index + 1} •{" "}
                                {ch.metadata?.location_label || `Page ${ch.page_number}`}
                              </span>
                              {isCited && (
                                <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 font-semibold text-[10px]">
                                  Cited Passage
                                </span>
                              )}
                            </div>
                            {ch.heading && (
                              <p className="text-[11px] font-medium text-blue-600 dark:text-blue-400 mb-1">
                                {ch.heading}
                              </p>
                            )}
                            <p className="text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed">
                              {ch.text}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </aside>
    </>
  );
}
