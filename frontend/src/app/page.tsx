"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  BookOpen,
  FolderKanban,
  Moon,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  Sun,
} from "lucide-react";
import Sidebar from "@/components/Sidebar";
import ModelSelector from "@/components/ModelSelector";
import MessageList from "@/components/MessageList";
import ChatComposer from "@/components/ChatComposer";
import DocumentContextPanel from "@/components/DocumentContextPanel";
import SettingsModal from "@/components/SettingsModal";
import {
  ChatMessage,
  Citation,
  Collection,
  Conversation,
  CragTrace,
  DocumentItem,
  HealthStatus,
  ModelInfo,
  RetrievalMode,
  UserSettings,
} from "@/types/api";
import {
  clearAllConversations,
  createCollection,
  createConversation,
  deleteCollection,
  deleteConversation,
  deleteDocument,
  fetchCollections,
  fetchConversation,
  fetchConversations,
  fetchDocuments,
  fetchHealth,
  fetchModels,
  fetchSettings,
  reindexDocument,
  streamChatMessage,
  updateConversation,
  updateSettings,
  uploadDocuments,
} from "@/lib/api";

export default function NeuralRagWorkspace() {
  // Layout & Panels
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [rightPanelTab, setRightPanelTab] = useState<"library" | "inspector">("library");
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Core Data State
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState<string>("default");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  // Active Chat Controls
  const [selectedModelId, setSelectedModelId] = useState<string>("gemini-3.1-flash-lite");
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>("corrective_rag");
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  // User Settings
  const [settings, setSettings] = useState<UserSettings>({
    theme: "dark",
    default_model: "gemini-3.1-flash-lite",
    retrieval_mode: "corrective_rag",
    top_k: 5,
    crag_threshold: 0.22,
    active_collection_id: "default",
    response_style: "comprehensive",
  });

  // Streaming & Upload States
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null);
  const [streamingTrace, setStreamingTrace] = useState<CragTrace | null>(null);
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Apply Dark/Light theme class to <html>
  useEffect(() => {
    const root = document.documentElement;
    if (settings.theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [settings.theme]);

  // Responsive initial sidebar state on mobile
  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, []);

  // Load initial workspace state from backend
  const loadWorkspaceData = useCallback(async () => {
    try {
      const [healthData, modelsData, colsData, settingsData, convsData] =
        await Promise.all([
          fetchHealth(),
          fetchModels(false),
          fetchCollections(),
          fetchSettings(),
          fetchConversations(""),
        ]);

      setHealth(healthData);
      setModels(modelsData.models);
      setCollections(colsData.collections);
      setSettings(settingsData);

      const initialColId = settingsData.active_collection_id || "default";
      setActiveCollectionId(initialColId);
      setSelectedModelId(settingsData.default_model || modelsData.default_model);
      setRetrievalMode(settingsData.retrieval_mode || "corrective_rag");
      setConversations(convsData.conversations);

      const docsData = await fetchDocuments(initialColId);
      setDocuments(docsData.documents);
    } catch (err: any) {
      setErrorMessage(
        err?.message || "Unable to connect to NeuralRAG FastAPI backend on port 8000."
      );
    }
  }, []);

  useEffect(() => {
    loadWorkspaceData();
  }, [loadWorkspaceData]);

  // Search conversations debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchConversations(searchQuery)
        .then((res) => setConversations(res.conversations))
        .catch(() => {});
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Keyboard shortcut Cmd/Ctrl + K for New Chat
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        handleNewChat();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const refreshCollectionAndDocs = async (colId: string) => {
    const [colsData, docsData] = await Promise.all([
      fetchCollections(),
      fetchDocuments(colId),
    ]);
    setCollections(colsData.collections);
    setDocuments(docsData.documents);
  };

  const handleSelectCollection = async (colId: string) => {
    setActiveCollectionId(colId);
    await refreshCollectionAndDocs(colId);
    await updateSettings({ active_collection_id: colId });
    if (activeConversation) {
      const updated = await updateConversation(activeConversation.id, {
        collection_id: colId,
      });
      setActiveConversation(updated);
    }
  };

  const handleSelectModel = async (modelId: string) => {
    setSelectedModelId(modelId);
    if (activeConversation) {
      try {
        const updated = await updateConversation(activeConversation.id, {
          model_id: modelId,
        });
        setActiveConversation(updated);
      } catch (err: any) {
        setErrorMessage(err?.message || "Failed to update conversation model.");
      }
    }
  };

  const handleChangeRetrievalMode = async (mode: RetrievalMode) => {
    setRetrievalMode(mode);
    if (activeConversation) {
      try {
        const updated = await updateConversation(activeConversation.id, {
          retrieval_mode: mode,
        });
        setActiveConversation(updated);
      } catch {
        // ignore
      }
    }
  };

  const handleNewChat = () => {
    if (isStreaming) handleStopGeneration();
    setActiveConversation(null);
    setMessages([]);
    setSelectedCitation(null);
    setErrorMessage(null);
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  };

  const handleSelectConversation = async (convId: string) => {
    if (isStreaming) handleStopGeneration();
    try {
      const fullConv = await fetchConversation(convId);
      setActiveConversation(fullConv);
      setMessages(fullConv.messages || []);
      setSelectedModelId(fullConv.model_id);
      setRetrievalMode(fullConv.retrieval_mode);
      if (fullConv.collection_id && fullConv.collection_id !== activeCollectionId) {
        setActiveCollectionId(fullConv.collection_id);
        await refreshCollectionAndDocs(fullConv.collection_id);
      }
      if (typeof window !== "undefined" && window.innerWidth < 1024) {
        setSidebarOpen(false);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || "Could not load conversation.");
    }
  };

  const handleRenameConversation = async (convId: string, newTitle: string) => {
    const updated = await updateConversation(convId, { title: newTitle });
    setConversations((prev) =>
      prev.map((c) => (c.id === convId ? { ...c, title: updated.title } : c))
    );
    if (activeConversation?.id === convId) {
      setActiveConversation(updated);
    }
  };

  const handleTogglePinConversation = async (convId: string, pinned: boolean) => {
    await updateConversation(convId, { pinned });
    const convsData = await fetchConversations(searchQuery);
    setConversations(convsData.conversations);
  };

  const handleDeleteConversation = async (convId: string) => {
    await deleteConversation(convId);
    setConversations((prev) => prev.filter((c) => c.id !== convId));
    if (activeConversation?.id === convId) {
      setActiveConversation(null);
      setMessages([]);
    }
  };

  const handleUploadFiles = async (files: File[]) => {
    if (files.length === 0) return;
    setIsUploading(true);
    setErrorMessage(null);
    try {
      const res = await uploadDocuments(activeCollectionId, files);
      const failed = res.uploaded.filter((d) => d.status === "error");
      if (failed.length > 0) {
        setErrorMessage(
          `Upload issue for ${failed[0].filename}: ${failed[0].error_message}`
        );
      }
      await refreshCollectionAndDocs(activeCollectionId);
    } catch (err: any) {
      setErrorMessage(err?.message || "Document upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendMessage = async (
    content: string,
    editMessageId?: string
  ) => {
    if (!content.trim() || isStreaming) return;
    setErrorMessage(null);

    let targetConv = activeConversation;
    try {
      if (!targetConv) {
        targetConv = await createConversation({
          title: "New Chat",
          collection_id: activeCollectionId,
          model_id: selectedModelId,
          retrieval_mode: retrievalMode,
        });
        setActiveConversation(targetConv);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to initialize conversation.");
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsStreaming(true);
    setStreamingContent("");
    setStreamingStatus("Retrieving & grading candidate passages...");
    setStreamingTrace(null);
    setStreamingCitations([]);

    // Optimistic update when editing an earlier message
    if (editMessageId) {
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === editMessageId);
        return idx >= 0 ? prev.slice(0, idx) : prev;
      });
    }

    try {
      await streamChatMessage(
        targetConv.id,
        {
          content,
          model_id: selectedModelId,
          retrieval_mode: retrievalMode,
          collection_id: activeCollectionId,
          top_k: settings.top_k,
          edit_message_id: editMessageId,
        },
        {
          onUserMessage: (userMsg, newTitle) => {
            setMessages((prev) => [...prev, userMsg]);
            setActiveConversation((prev) =>
              prev ? { ...prev, title: newTitle } : prev
            );
          },
          onStatus: (_stage, detail) => {
            setStreamingStatus(detail);
          },
          onCragTrace: (trace, citations) => {
            setStreamingTrace(trace);
            setStreamingCitations(citations);
          },
          onToken: (delta) => {
            setStreamingContent((prev) => prev + delta);
          },
          onDone: (assistantMsg) => {
            setMessages((prev) => [...prev, assistantMsg]);
            setStreamingContent("");
            setStreamingStatus(null);
            setStreamingTrace(null);
          },
        },
        controller.signal
      );

      // Refresh sidebar conversation list order
      const convsData = await fetchConversations(searchQuery);
      setConversations(convsData.conversations);
    } catch (err: any) {
      if (err?.name === "AbortError") {
        // User clicked Stop Generation; reload conversation state from DB
        const updatedConv = await fetchConversation(targetConv.id);
        setMessages(updatedConv.messages || []);
      } else {
        setErrorMessage(err?.message || "Error generating response.");
      }
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
      setStreamingStatus(null);
      abortControllerRef.current = null;
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const handleSelectCitation = (citation: Citation) => {
    setSelectedCitation(citation);
    setRightPanelTab("inspector");
    setRightPanelOpen(true);
  };

  const activeCollection =
    collections.find((c) => c.id === activeCollectionId) || {
      id: "default",
      name: "General Workspace",
    };

  const activeModelObj =
    models.find((m) => m.id === selectedModelId) || models[0];

  return (
    <div className="flex h-dvh w-screen overflow-hidden bg-white dark:bg-zinc-950">
      {/* A. LEFT SIDEBAR */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        conversations={conversations}
        activeConversationId={activeConversation?.id || null}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onRenameConversation={handleRenameConversation}
        onTogglePinConversation={handleTogglePinConversation}
        onDeleteConversation={handleDeleteConversation}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        collections={collections}
        activeCollectionId={activeCollectionId}
        onSelectCollection={handleSelectCollection}
        documentCount={documents.length}
        onOpenDocumentLibrary={() => {
          setRightPanelTab("library");
          setRightPanelOpen(true);
        }}
        theme={settings.theme}
        onToggleTheme={async () => {
          const nextTheme = settings.theme === "dark" ? "light" : "dark";
          const updated = await updateSettings({ theme: nextTheme });
          setSettings(updated);
        }}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {/* B. MAIN CHAT WORKSPACE */}
      <main className="flex-1 flex flex-col min-w-0 h-full relative">
        {/* Top Navigation Bar */}
        <header className="h-14 px-3 sm:px-4 border-b border-zinc-200/70 dark:border-zinc-800/70 flex items-center justify-between gap-2 shrink-0 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md z-20">
          <div className="flex items-center gap-2 min-w-0">
            {!sidebarOpen && (
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setSidebarOpen(true)}
                  title="Expand sidebar"
                  aria-label="Expand sidebar"
                  className="p-2 rounded-xl text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                >
                  <PanelLeftOpen className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={handleNewChat}
                  title="New Chat"
                  aria-label="New Chat"
                  className="p-2 rounded-xl text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Gemini Model Selector Dropdown */}
            <ModelSelector
              models={models}
              selectedModelId={selectedModelId}
              onSelectModel={handleSelectModel}
              onRefreshModels={async (verifyLive = false) => {
                const res = await fetchModels(verifyLive);
                setModels(res.models);
              }}
              disabled={isStreaming}
            />

            {activeConversation && (
              <span className="hidden md:inline-block text-xs text-zinc-400 dark:text-zinc-500 truncate max-w-[200px] border-l border-zinc-200 dark:border-zinc-800 pl-2.5">
                {activeConversation.title}
              </span>
            )}
          </div>

          {/* Right Header Controls: Collection Badge, Theme Toggle, Document Context Drawer Toggle */}
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={() => {
                setRightPanelTab("library");
                setRightPanelOpen(true);
              }}
              className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium bg-zinc-100 hover:bg-zinc-200/70 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200/60 dark:border-zinc-800 transition-colors"
              title="Switch or manage active document collection"
            >
              <FolderKanban className="w-3.5 h-3.5 text-blue-500" />
              <span className="truncate max-w-[130px]">{activeCollection.name}</span>
              <span className="px-1.5 py-0.2 rounded-full bg-zinc-200 dark:bg-zinc-800 text-[10px]">
                {documents.length}
              </span>
            </button>

            <button
              type="button"
              onClick={async () => {
                const nextTheme = settings.theme === "dark" ? "light" : "dark";
                const updated = await updateSettings({ theme: nextTheme });
                setSettings(updated);
              }}
              title={
                settings.theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"
              }
              aria-label="Toggle theme"
              className="p-2 rounded-xl text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            >
              {settings.theme === "dark" ? (
                <Sun className="w-4 h-4 text-amber-400" />
              ) : (
                <Moon className="w-4 h-4 text-zinc-700" />
              )}
            </button>

            <button
              type="button"
              onClick={() => setRightPanelOpen((prev) => !prev)}
              title={
                rightPanelOpen
                  ? "Hide Document & Citation Panel"
                  : "Show Document & Citation Panel"
              }
              aria-label="Toggle Document Panel"
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-colors ${
                rightPanelOpen
                  ? "bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800/70 text-blue-600 dark:text-blue-400"
                  : "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
              }`}
            >
              {rightPanelOpen ? (
                <PanelRightClose className="w-4 h-4" />
              ) : (
                <PanelRightOpen className="w-4 h-4" />
              )}
              <span className="hidden sm:inline">Sources</span>
            </button>
          </div>
        </header>

        {/* Main Scrollable Conversation Area */}
        <MessageList
          messages={messages}
          isStreaming={isStreaming}
          streamingContent={streamingContent}
          streamingStatus={streamingStatus}
          streamingTrace={streamingTrace}
          streamingCitations={streamingCitations}
          activeCollectionName={activeCollection.name}
          documentCount={documents.length}
          onSelectStarterPrompt={(prompt) => handleSendMessage(prompt)}
          onEditAndResubmit={async (msgId, newContent) => {
            await handleSendMessage(newContent, msgId);
          }}
          onRetryMessage={async (userMsg) => {
            await handleSendMessage(userMsg.content, userMsg.id);
          }}
          onSelectCitation={handleSelectCitation}
          onOpenUploadPanel={() => {
            setRightPanelTab("library");
            setRightPanelOpen(true);
          }}
        />

        {/* Bottom ChatGPT-Style Message Composer */}
        <ChatComposer
          onSendMessage={(content) => handleSendMessage(content)}
          onStopGeneration={handleStopGeneration}
          onUploadFiles={handleUploadFiles}
          isStreaming={isStreaming}
          isUploading={isUploading}
          retrievalMode={retrievalMode}
          onChangeRetrievalMode={handleChangeRetrievalMode}
          activeModelName={
            activeModelObj ? activeModelObj.display_name : selectedModelId
          }
          activeCollectionName={activeCollection.name}
          documentCount={documents.length}
          errorMessage={errorMessage}
          onClearError={() => setErrorMessage(null)}
        />
      </main>

      {/* C. OPTIONAL DOCUMENT CONTEXT & CITATION INSPECTOR PANEL */}
      <DocumentContextPanel
        isOpen={rightPanelOpen}
        onClose={() => setRightPanelOpen(false)}
        activeTab={rightPanelTab}
        onTabChange={setRightPanelTab}
        collections={collections}
        activeCollectionId={activeCollectionId}
        onSelectCollection={handleSelectCollection}
        onCreateCollection={async (name, desc) => {
          const newCol = await createCollection(name, desc);
          await handleSelectCollection(newCol.id);
        }}
        onDeleteCollection={async (colId) => {
          await deleteCollection(colId);
          await handleSelectCollection("default");
        }}
        documents={documents}
        isUploading={isUploading}
        onUploadFiles={handleUploadFiles}
        onReindexDocument={async (docId) => {
          await reindexDocument(docId);
          await refreshCollectionAndDocs(activeCollectionId);
        }}
        onDeleteDocument={async (docId) => {
          await deleteDocument(docId);
          await refreshCollectionAndDocs(activeCollectionId);
        }}
        selectedCitation={selectedCitation}
      />

      {/* SETTINGS & DIAGNOSTICS MODAL */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        models={models}
        health={health}
        onUpdateSettings={async (updates) => {
          const updated = await updateSettings(updates);
          setSettings(updated);
          if (updates.default_model && !activeConversation) {
            setSelectedModelId(updates.default_model);
          }
          if (updates.retrieval_mode && !activeConversation) {
            setRetrievalMode(updates.retrieval_mode);
          }
        }}
        onClearAllConversations={async () => {
          await clearAllConversations();
          setConversations([]);
          setActiveConversation(null);
          setMessages([]);
        }}
      />
    </div>
  );
}
