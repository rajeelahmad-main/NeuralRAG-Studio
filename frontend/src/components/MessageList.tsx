"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowDown,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  Edit3,
  FileSpreadsheet,
  FileText,
  GitCompare,
  Layers,
  Loader2,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  User,
} from "lucide-react";
import { ChatMessage, Citation, CragTrace } from "@/types/api";

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
  streamingStatus: string | null;
  streamingTrace: CragTrace | null;
  streamingCitations: Citation[];
  activeCollectionName: string;
  documentCount: number;
  onSelectStarterPrompt: (prompt: string) => void;
  onEditAndResubmit: (messageId: string, newContent: string) => Promise<void>;
  onRetryMessage: (userMessage: ChatMessage) => Promise<void>;
  onSelectCitation: (citation: Citation) => void;
  onOpenUploadPanel: () => void;
}

const STARTER_PROMPTS = [
  {
    title: "Executive Summary",
    prompt: "Summarize the key findings, main arguments, and conclusions across my uploaded documents.",
    badge: "Overview",
  },
  {
    title: "Cross-Document Comparison",
    prompt: "Compare the key claims, quantitative metrics, and conclusions across the uploaded files and highlight any discrepancies.",
    badge: "Compare Mode",
  },
  {
    title: "Extract Financial & Tabular Metrics",
    prompt: "What quantitative figures, tables, or performance metrics are reported in these documents?",
    badge: "Data & Tables",
  },
  {
    title: "Methodology & Architecture Audit",
    prompt: "Explain the core methodology, system architecture, or security controls described in the uploaded text.",
    badge: "Deep Dive",
  },
  {
    title: "Study Guide & Verification Quiz",
    prompt: "Generate a concise study guide and a 3-question comprehension quiz with answers grounded strictly in the uploaded files.",
    badge: "CRISP Lab",
  },
];

export default function MessageList({
  messages,
  isStreaming,
  streamingContent,
  streamingStatus,
  streamingTrace,
  streamingCitations,
  activeCollectionName,
  documentCount,
  onSelectStarterPrompt,
  onEditAndResubmit,
  onRetryMessage,
  onSelectCitation,
  onOpenUploadPanel,
}: MessageListProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomAnchorRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [editingMsgId, setEditingMsgId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [expandedTraces, setExpandedTraces] = useState<Record<string, boolean>>({});

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    bottomAnchorRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    if (!showScrollBottom) {
      scrollToBottom("smooth");
    }
  }, [messages.length, streamingContent, streamingStatus]);

  const handleScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBottom(distanceFromBottom > 180);
  };

  const handleCopyText = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1800);
    } catch {
      // ignore clipboard errors
    }
  };

  const toggleTrace = (msgId: string) => {
    setExpandedTraces((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  /**
   * Transforms inline [Source N] markers into markdown links `#citation-N`
   * so ReactMarkdown renders them as interactive citation pills.
   */
  const preprocessCitationsInMarkdown = (rawText: string) => {
    return rawText.replace(/\[Source\s+(\d+)\]/gi, "[Source $1](#citation-$1)");
  };

  const renderMarkdownWithCitations = (content: string, citations: Citation[], msgKey: string) => {
    const processed = preprocessCitationsInMarkdown(content);

    return (
      <div className="prose prose-zinc dark:prose-invert max-w-none text-sm sm:text-[15px] leading-relaxed break-words">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({ href, children }) => {
              if (href && href.startsWith("#citation-")) {
                const idx = parseInt(href.replace("#citation-", ""), 10);
                const cit = citations.find((c) => c.citation_index === idx) || citations[idx - 1];
                return (
                  <button
                    type="button"
                    onClick={() => {
                      if (cit) onSelectCitation(cit);
                    }}
                    title={
                      cit
                        ? `${cit.filename} • ${cit.location_label} (Score: ${cit.score})`
                        : `Inspect Source ${idx}`
                    }
                    className="inline-flex items-center gap-1 mx-0.5 px-2 py-0.5 text-[11px] font-semibold rounded-full bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/25 transition-colors align-baseline cursor-pointer"
                  >
                    <BookOpen className="w-2.5 h-2.5 shrink-0" />
                    <span>{children}</span>
                  </button>
                );
              }
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 underline hover:opacity-80"
                >
                  {children}
                </a>
              );
            },
            code: ({ className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || "");
              const codeString = String(children).replace(/\n$/, "");
              const isBlock = Boolean(match || codeString.includes("\n"));

              if (!isBlock) {
                return (
                  <code
                    className="px-1.5 py-0.5 rounded-md bg-zinc-200/70 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 font-mono text-[13px]"
                    {...props}
                  >
                    {children}
                  </code>
                );
              }

              const codeId = `${msgKey}-${codeString.slice(0, 16)}`;
              return (
                <div className="my-3 rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800 bg-zinc-950 text-zinc-100">
                  <div className="flex items-center justify-between px-3.5 py-1.5 bg-zinc-900 border-b border-zinc-800 text-xs text-zinc-400">
                    <span className="font-mono">{match ? match[1] : "code"}</span>
                    <button
                      type="button"
                      onClick={() => handleCopyText(codeId, codeString)}
                      className="inline-flex items-center gap-1 text-zinc-400 hover:text-white transition-colors"
                    >
                      {copiedId === codeId ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy code</span>
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-3.5 overflow-x-auto text-xs sm:text-[13px] font-mono leading-relaxed">
                    <code>{codeString}</code>
                  </pre>
                </div>
              );
            },
            table: ({ children }) => (
              <div className="my-3 overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
                <table className="w-full text-left border-collapse text-xs sm:text-sm">
                  {children}
                </table>
              </div>
            ),
            th: ({ children }) => (
              <th className="px-3 py-2 bg-zinc-100 dark:bg-zinc-800/80 border-b border-zinc-200 dark:border-zinc-700 font-semibold text-zinc-800 dark:text-zinc-200">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="px-3 py-2 border-b border-zinc-100 dark:border-zinc-800/60 text-zinc-700 dark:text-zinc-300">
                {children}
              </td>
            ),
          }}
        >
          {processed}
        </ReactMarkdown>
      </div>
    );
  };

  const renderCragTracePill = (msgId: string, trace?: CragTrace) => {
    if (!trace || !trace.mode) return null;
    const isExpanded = Boolean(expandedTraces[msgId]);

    const modeBadge =
      trace.mode === "corrective_rag"
        ? "Corrective RAG"
        : trace.mode === "compare_documents"
        ? "Compare Documents"
        : "Document Search";

    const statusColor =
      trace.status === "sufficient"
        ? "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
        : trace.status === "ambiguous"
        ? "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20"
        : "text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20";

    return (
      <div className="mb-2">
        <button
          type="button"
          onClick={() => toggleTrace(msgId)}
          className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg text-xs font-medium bg-zinc-100 dark:bg-zinc-900 hover:bg-zinc-200/70 dark:hover:bg-zinc-800/80 text-zinc-600 dark:text-zinc-400 border border-zinc-200/80 dark:border-zinc-800 transition-colors"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
          <span>{modeBadge}</span>
          <span className={`px-1.5 py-0.2 rounded text-[10px] border ${statusColor}`}>
            {trace.final_evidence_count} verified sources
          </span>
          {trace.retries_used > 0 && (
            <span className="px-1.5 py-0.2 rounded text-[10px] bg-blue-500/10 text-blue-600 dark:text-blue-400">
              +{trace.retries_used} query rewrite
            </span>
          )}
          {isExpanded ? (
            <ChevronDown className="w-3.5 h-3.5 opacity-60" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 opacity-60" />
          )}
        </button>

        {isExpanded && (
          <div className="mt-1.5 p-3 rounded-xl bg-zinc-50 dark:bg-zinc-900/90 border border-zinc-200/80 dark:border-zinc-800 text-xs space-y-1.5 text-zinc-600 dark:text-zinc-400 animate-in fade-in duration-150">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="p-2 rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/80">
                <p className="text-[10px] uppercase text-zinc-400">Evidence Status</p>
                <p className="font-semibold text-zinc-800 dark:text-zinc-200 capitalize">
                  {trace.status.replace(/_/g, " ")}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/80">
                <p className="text-[10px] uppercase text-zinc-400">Top Relevance</p>
                <p className="font-semibold text-zinc-800 dark:text-zinc-200">
                  {(trace.confidence * 100).toFixed(1)}%
                </p>
              </div>
              <div className="p-2 rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/80">
                <p className="text-[10px] uppercase text-zinc-400">Candidates Graded</p>
                <p className="font-semibold text-zinc-800 dark:text-zinc-200">
                  {trace.initial_candidates} chunks
                </p>
              </div>
              <div className="p-2 rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/80">
                <p className="text-[10px] uppercase text-zinc-400">CRAG Rewrites</p>
                <p className="font-semibold text-zinc-800 dark:text-zinc-200">
                  {trace.retries_used} retries
                </p>
              </div>
            </div>

            {trace.rewritten_queries && trace.rewritten_queries.length > 0 && (
              <div className="pt-1">
                <p className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">
                  Corrective Query Expansions Executed:
                </p>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {trace.rewritten_queries.map((rq, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 font-mono text-[11px]"
                    >
                      &ldquo;{rq}&rdquo;
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderCitationsFooter = (citations: Citation[]) => {
    if (!citations || citations.length === 0) return null;
    return (
      <div className="mt-3 pt-2.5 border-t border-zinc-200/60 dark:border-zinc-800/70">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-1.5">
          Verified Source Citations ({citations.length})
        </p>
        <div className="flex flex-wrap gap-1.5">
          {citations.map((cit) => (
            <button
              key={`${cit.chunk_id}-${cit.citation_index}`}
              type="button"
              onClick={() => onSelectCitation(cit)}
              className="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs bg-zinc-100 hover:bg-blue-50 dark:bg-zinc-900 dark:hover:bg-blue-950/40 border border-zinc-200/80 hover:border-blue-300 dark:border-zinc-800 dark:hover:border-blue-800/70 text-zinc-700 dark:text-zinc-300 transition-all"
            >
              <span className="px-1.5 py-0.2 rounded-md bg-blue-600 text-white text-[10px] font-bold">
                {cit.citation_index}
              </span>
              {cit.sheet_name ? (
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
              ) : (
                <FileText className="w-3.5 h-3.5 text-blue-500 shrink-0" />
              )}
              <span className="font-medium truncate max-w-[160px]">{cit.filename}</span>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
                • {cit.location_label}
              </span>
            </button>
          ))}
        </div>
      </div>
    );
  };

  // Centered Initial Welcome Screen when no messages exist
  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 overflow-y-auto px-4 py-8 flex flex-col items-center justify-center">
        <div className="w-full max-w-2xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-md mx-auto">
            <Sparkles className="w-6 h-6" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              What would you like to know from your documents?
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-lg mx-auto">
              Ask questions across PDF, Word, Excel, CSV, and Markdown files with{" "}
              <span className="text-zinc-700 dark:text-zinc-200 font-medium">
                Corrective RAG verification
              </span>{" "}
              and clickable source citations.
            </p>
          </div>

          {/* Upload CTA if collection has 0 documents */}
          {documentCount === 0 && (
            <div className="p-4 rounded-2xl bg-blue-50/60 dark:bg-blue-950/20 border border-blue-200/70 dark:border-blue-900/50 flex flex-col sm:flex-row items-center justify-between gap-3 text-left">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-blue-600/10 text-blue-600 dark:text-blue-400">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                    No documents in &ldquo;{activeCollectionName}&rdquo; yet
                  </p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">
                    Upload PDFs, DOCX, spreadsheets, or notes to ground your answers.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onOpenUploadPanel}
                className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shrink-0 transition-colors"
              >
                Upload Documents
              </button>
            </div>
          )}

          {/* 5 Starter Prompt Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left pt-2">
            {STARTER_PROMPTS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectStarterPrompt(item.prompt)}
                className={`group p-3.5 rounded-2xl bg-white dark:bg-zinc-900/80 hover:bg-zinc-50 dark:hover:bg-zinc-800/80 border border-zinc-200/80 dark:border-zinc-800/90 transition-all text-left flex flex-col justify-between gap-2 shadow-2xs ${
                  idx === 4 ? "sm:col-span-2" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {item.title}
                  </span>
                  <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
                    {item.badge}
                  </span>
                </div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-relaxed">
                  {item.prompt}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={scrollContainerRef}
      onScroll={handleScroll}
      className="relative flex-1 overflow-y-auto px-3 sm:px-6 py-6"
    >
      <div className="max-w-3xl mx-auto space-y-6 pb-6">
        {messages.map((msg, index) => {
          const isUser = msg.role === "user";
          const isEditing = editingMsgId === msg.id;
          const previousUserMsg =
            !isUser && index > 0 && messages[index - 1].role === "user"
              ? messages[index - 1]
              : null;

          if (isUser) {
            return (
              <div key={msg.id} className="flex flex-col items-end group">
                <div className="flex items-start gap-2.5 max-w-[88%] sm:max-w-[80%]">
                  {isEditing ? (
                    <div className="w-full min-w-[280px] sm:min-w-[420px] p-3 rounded-2xl bg-zinc-100 dark:bg-zinc-800 border border-blue-500 space-y-2">
                      <textarea
                        rows={3}
                        value={editingText}
                        onChange={(e) => setEditingText(e.target.value)}
                        className="w-full bg-transparent text-sm text-zinc-900 dark:text-zinc-100 focus:outline-none resize-none"
                      />
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setEditingMsgId(null)}
                          className="px-3 py-1 rounded-lg text-xs font-medium bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-200"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            if (!editingText.trim()) return;
                            const text = editingText.trim();
                            setEditingMsgId(null);
                            await onEditAndResubmit(msg.id, text);
                          }}
                          className="px-3 py-1 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white"
                        >
                          Save & Submit
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="px-4 py-2.5 rounded-3xl rounded-tr-lg bg-zinc-900 dark:bg-zinc-800 text-white dark:text-zinc-100 text-sm sm:text-[15px] leading-relaxed shadow-2xs">
                      <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                    </div>
                  )}
                </div>

                {/* User Message Actions: Edit & Timestamp */}
                {!isEditing && (
                  <div className="flex items-center gap-2 mt-1 px-1 opacity-0 group-hover:opacity-100 transition-opacity text-[11px] text-zinc-400">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingMsgId(msg.id);
                        setEditingText(msg.content);
                      }}
                      className="inline-flex items-center gap-1 hover:text-zinc-700 dark:hover:text-zinc-200"
                      title="Edit and resubmit message"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>Edit</span>
                    </button>
                    <span>•</span>
                    <span>
                      {new Date(msg.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                )}
              </div>
            );
          }

          // Assistant Message
          const isLastAssistant = index === messages.length - 1 && !isStreaming;

          return (
            <div key={msg.id} className="flex items-start gap-3 sm:gap-4 group">
              <div className="w-8 h-8 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                <Sparkles className="w-4 h-4" />
              </div>

              <div className="flex-1 min-w-0">
                {/* CRAG Trace Pill */}
                {renderCragTracePill(msg.id, msg.crag_trace)}

                {/* Markdown Content with Interactive [Source N] Badges */}
                {renderMarkdownWithCitations(msg.content, msg.citations || [], msg.id)}

                {/* Verified Citations Footer */}
                {renderCitationsFooter(msg.citations || [])}

                {/* Assistant Action Bar: Copy, Retry, Model Badge, Latency */}
                <div className="flex items-center flex-wrap gap-3 mt-2.5 text-xs text-zinc-400 dark:text-zinc-500">
                  <button
                    type="button"
                    onClick={() => handleCopyText(msg.id, msg.content)}
                    className="inline-flex items-center gap-1 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
                    title="Copy response"
                  >
                    {copiedId === msg.id ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-500" />
                        <span className="text-emerald-500">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>

                  {previousUserMsg && (
                    <button
                      type="button"
                      onClick={() => onRetryMessage(previousUserMsg)}
                      className="inline-flex items-center gap-1 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
                      title="Regenerate response"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Retry</span>
                    </button>
                  )}

                  {msg.model_id && (
                    <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-900 text-zinc-500">
                      {msg.model_id}
                    </span>
                  )}

                  {msg.latency_ms > 0 && (
                    <span className="text-[11px]">{(msg.latency_ms / 1000).toFixed(2)}s</span>
                  )}
                </div>

                {/* Contextual Follow-up Suggestions on latest message */}
                {isLastAssistant && msg.follow_ups && msg.follow_ups.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800/60 space-y-1.5">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                      Suggested Follow-ups
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.follow_ups.map((q, qIdx) => (
                        <button
                          key={qIdx}
                          type="button"
                          onClick={() => onSelectStarterPrompt(q)}
                          className="text-left px-3 py-1.5 rounded-xl text-xs bg-zinc-100/80 hover:bg-zinc-200/70 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200/60 dark:border-zinc-800 transition-colors"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Active Streaming Assistant Bubble */}
        {isStreaming && (
          <div className="flex items-start gap-3 sm:gap-4 animate-in fade-in duration-150">
            <div className="w-8 h-8 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>

            <div className="flex-1 min-w-0 space-y-2">
              {streamingStatus && !streamingContent && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-zinc-100 dark:bg-zinc-900 text-xs text-zinc-600 dark:text-zinc-300 border border-zinc-200/70 dark:border-zinc-800">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
                  <span>{streamingStatus}</span>
                </div>
              )}

              {streamingTrace && renderCragTracePill("streaming-trace", streamingTrace)}

              {streamingContent &&
                renderMarkdownWithCitations(
                  streamingContent,
                  streamingCitations,
                  "streaming-msg"
                )}
            </div>
          </div>
        )}

        <div ref={bottomAnchorRef} />
      </div>

      {/* Floating Scroll-to-latest Button */}
      {showScrollBottom && (
        <button
          type="button"
          onClick={() => scrollToBottom("smooth")}
          aria-label="Scroll to latest message"
          className="fixed bottom-28 right-6 lg:right-10 z-20 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shadow-lg text-xs font-medium text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-all"
        >
          <ArrowDown className="w-3.5 h-3.5" />
          <span>Scroll to latest</span>
        </button>
      )}
    </div>
  );
}
