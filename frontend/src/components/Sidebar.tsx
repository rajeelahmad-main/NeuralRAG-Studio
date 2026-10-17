"use client";

import React, { useMemo, useState } from "react";
import {
  BookOpen,
  Check,
  Edit3,
  FolderKanban,
  MessageSquare,
  Moon,
  PanelLeftClose,
  Pin,
  Plus,
  Search,
  Settings,
  Sparkles,
  Sun,
  Trash2,
  X,
} from "lucide-react";
import { Collection, Conversation } from "@/types/api";

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (convId: string) => void;
  onNewChat: () => void;
  onRenameConversation: (convId: string, newTitle: string) => Promise<void>;
  onTogglePinConversation: (convId: string, pinned: boolean) => Promise<void>;
  onDeleteConversation: (convId: string) => Promise<void>;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  collections: Collection[];
  activeCollectionId: string;
  onSelectCollection: (colId: string) => void;
  documentCount: number;
  onOpenDocumentLibrary: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onOpenSettings: () => void;
}

export default function Sidebar({
  isOpen,
  onToggle,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onRenameConversation,
  onTogglePinConversation,
  onDeleteConversation,
  searchQuery,
  onSearchChange,
  collections,
  activeCollectionId,
  onSelectCollection,
  documentCount,
  onOpenDocumentLibrary,
  theme,
  onToggleTheme,
  onOpenSettings,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const groupedConversations = useMemo(() => {
    const pinned: Conversation[] = [];
    const today: Conversation[] = [];
    const prev7Days: Conversation[] = [];
    const older: Conversation[] = [];

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const sevenDaysAgo = startOfToday - 7 * 24 * 60 * 60 * 1000;

    for (const c of conversations) {
      if (c.pinned) {
        pinned.push(c);
        continue;
      }
      const updatedTime = new Date(c.updated_at).getTime();
      if (updatedTime >= startOfToday) {
        today.push(c);
      } else if (updatedTime >= sevenDaysAgo) {
        prev7Days.push(c);
      } else {
        older.push(c);
      }
    }

    return [
      { label: "Pinned", items: pinned },
      { label: "Today", items: today },
      { label: "Previous 7 Days", items: prev7Days },
      { label: "Older", items: older },
    ].filter((g) => g.items.length > 0);
  }, [conversations]);

  const startEditing = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditingTitle(conv.title);
    setConfirmDeleteId(null);
  };

  const saveEdit = async (e: React.MouseEvent | React.FormEvent, convId: string) => {
    e.stopPropagation();
    if (editingTitle.trim()) {
      await onRenameConversation(convId, editingTitle.trim());
    }
    setEditingId(null);
  };

  const renderConvItem = (conv: Conversation) => {
    const isActive = conv.id === activeConversationId;
    const isEditing = editingId === conv.id;
    const isConfirmingDelete = confirmDeleteId === conv.id;

    return (
      <div
        key={conv.id}
        onClick={() => {
          if (!isEditing && !isConfirmingDelete) {
            onSelectConversation(conv.id);
          }
        }}
        className={`group relative flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-colors cursor-pointer ${
          isActive
            ? "bg-zinc-200/80 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-medium"
            : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 hover:text-zinc-900 dark:hover:text-zinc-200"
        }`}
      >
        <MessageSquare className="w-4 h-4 shrink-0 opacity-70" />

        {isEditing ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              saveEdit(e, conv.id);
            }}
            className="flex items-center gap-1 flex-1 min-w-0"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="text"
              value={editingTitle}
              onChange={(e) => setEditingTitle(e.target.value)}
              autoFocus
              className="w-full px-2 py-0.5 text-xs rounded-md bg-white dark:bg-zinc-900 border border-blue-500 text-zinc-900 dark:text-zinc-100 focus:outline-none"
            />
            <button
              type="submit"
              className="p-1 text-emerald-600 hover:bg-emerald-500/10 rounded"
              title="Save title"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setEditingId(null)}
              className="p-1 text-zinc-400 hover:bg-zinc-500/10 rounded"
              title="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </form>
        ) : isConfirmingDelete ? (
          <div
            className="flex items-center justify-between flex-1 min-w-0 gap-1"
            onClick={(e) => e.stopPropagation()}
          >
            <span className="text-xs text-rose-600 dark:text-rose-400 font-medium truncate">
              Delete chat?
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={async () => {
                  await onDeleteConversation(conv.id);
                  setConfirmDeleteId(null);
                }}
                className="px-2 py-0.5 text-[11px] font-medium rounded bg-rose-600 text-white hover:bg-rose-500"
              >
                Delete
              </button>
              <button
                type="button"
                onClick={() => setConfirmDeleteId(null)}
                className="px-1.5 py-0.5 text-[11px] rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300"
              >
                No
              </button>
            </div>
          </div>
        ) : (
          <>
            <span className="truncate flex-1">{conv.title || "New Chat"}</span>
            <div
              className={`flex items-center gap-0.5 ${
                isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
              } transition-opacity`}
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onTogglePinConversation(conv.id, !conv.pinned);
                }}
                title={conv.pinned ? "Unpin conversation" : "Pin conversation"}
                className={`p-1 rounded-md hover:bg-zinc-300/60 dark:hover:bg-zinc-700/60 ${
                  conv.pinned ? "text-amber-500" : "text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                }`}
              >
                <Pin className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={(e) => startEditing(e, conv)}
                title="Rename conversation"
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-300/60 dark:hover:bg-zinc-700/60"
              >
                <Edit3 className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDeleteId(conv.id);
                }}
                title="Delete conversation"
                className="p-1 rounded-md text-zinc-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-500/10"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onToggle}
          className="fixed inset-0 bg-black/40 backdrop-blur-[1px] z-30 lg:hidden"
        />
      )}

      <aside
        aria-label="Conversation and Document Sidebar"
        className={`fixed lg:static inset-y-0 left-0 z-40 flex flex-col bg-zinc-50 dark:bg-zinc-950 border-r border-zinc-200/80 dark:border-zinc-800/80 transition-all duration-200 ease-in-out ${
          isOpen
            ? "w-[280px] translate-x-0"
            : "w-0 -translate-x-full lg:w-0 lg:border-r-0 overflow-hidden"
        }`}
      >
        <div className="flex flex-col h-full w-[280px]">
          {/* Header: Brand + Collapse */}
          <div className="flex items-center justify-between px-3.5 py-3 border-b border-zinc-200/60 dark:border-zinc-800/60">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 flex items-center justify-center shadow-sm">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h1 className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-100 leading-none">
                  NeuralRAG
                </h1>
                <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                  CRISP + Corrective RAG
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={onToggle}
              title="Collapse sidebar"
              className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800 transition-colors"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* Primary Actions: New Chat & Document Library */}
          <div className="p-3 space-y-2">
            <button
              type="button"
              onClick={onNewChat}
              className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 text-sm font-medium shadow-sm transition-all"
            >
              <span className="flex items-center gap-2">
                <Plus className="w-4 h-4 stroke-[2.5]" />
                New Chat
              </span>
              <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-white/15 dark:bg-zinc-900/10 font-mono">
                ⌘K
              </kbd>
            </button>

            {/* Active Collection Selector & Library Button */}
            <div className="flex items-center gap-1.5">
              <div className="relative flex-1 min-w-0">
                <FolderKanban className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <select
                  aria-label="Active Document Collection"
                  value={activeCollectionId}
                  onChange={(e) => onSelectCollection(e.target.value)}
                  className="w-full pl-8 pr-6 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/40 truncate"
                >
                  {collections.map((col) => (
                    <option key={col.id} value={col.id}>
                      {col.name} ({col.document_count ?? 0})
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                onClick={onOpenDocumentLibrary}
                title="Open Document Library & Context Panel"
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors shrink-0"
              >
                <BookOpen className="w-3.5 h-3.5 text-blue-500" />
                <span>{documentCount}</span>
              </button>
            </div>

            {/* Search Conversations */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder="Search conversations..."
                className="w-full pl-8 pr-7 py-1.5 text-xs rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-transparent focus:border-zinc-300 dark:focus:border-zinc-700 text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none transition-colors"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => onSearchChange("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Conversation History List */}
          <div className="flex-1 overflow-y-auto px-2.5 py-1 space-y-4">
            {groupedConversations.length === 0 ? (
              <div className="text-center py-8 px-4">
                <MessageSquare className="w-6 h-6 text-zinc-300 dark:text-zinc-700 mx-auto mb-2" />
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {searchQuery ? "No matching conversations found." : "No conversations yet."}
                </p>
              </div>
            ) : (
              groupedConversations.map((group) => (
                <div key={group.label} className="space-y-0.5">
                  <p className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                    {group.label}
                  </p>
                  {group.items.map(renderConvItem)}
                </div>
              ))
            )}
          </div>

          {/* Footer: Document Workspace CTA, Theme Toggle & Settings */}
          <div className="p-3 border-t border-zinc-200/80 dark:border-zinc-800/80 space-y-1">
            <button
              type="button"
              onClick={onOpenDocumentLibrary}
              className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/70 transition-colors"
            >
              <span className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-blue-500" />
                Document Library
              </span>
              <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                {documentCount} files
              </span>
            </button>

            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={onOpenSettings}
                className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/70 transition-colors flex-1"
              >
                <Settings className="w-4 h-4" />
                <span>Settings & RAG Config</span>
              </button>

              <button
                type="button"
                onClick={onToggleTheme}
                title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
                aria-label="Toggle color theme"
                className="p-2 rounded-xl text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/70 transition-colors"
              >
                {theme === "dark" ? (
                  <Sun className="w-4 h-4 text-amber-400" />
                ) : (
                  <Moon className="w-4 h-4 text-zinc-700" />
                )}
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
