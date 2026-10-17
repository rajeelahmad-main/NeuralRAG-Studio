"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Moon,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sun,
  Trash2,
  X,
} from "lucide-react";
import {
  HealthStatus,
  ModelInfo,
  RetrievalMode,
  UserSettings,
} from "@/types/api";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: UserSettings;
  models: ModelInfo[];
  health: HealthStatus | null;
  onUpdateSettings: (updates: Partial<UserSettings>) => Promise<void>;
  onClearAllConversations: () => Promise<void>;
}

export default function SettingsModal({
  isOpen,
  onClose,
  settings,
  models,
  health,
  onUpdateSettings,
  onClearAllConversations,
}: SettingsModalProps) {
  const [confirmClear, setConfirmClear] = useState(false);
  const [saving, setSaving] = useState(false);

  if (!isOpen) return null;

  const handleFieldChange = async (updates: Partial<UserSettings>) => {
    setSaving(true);
    try {
      await onUpdateSettings(updates);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-modal-title"
        className="w-full max-w-lg rounded-3xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200/80 dark:border-zinc-800">
          <div className="flex items-center gap-2.5">
            <Sliders className="w-4 h-4 text-blue-500" />
            <h2
              id="settings-modal-title"
              className="text-base font-semibold text-zinc-900 dark:text-zinc-100"
            >
              Workspace Settings & RAG Configuration
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-xl text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {/* Server API Security & Health Status */}
          <div className="p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/80 dark:border-zinc-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                Server API Key & Security Status
              </span>
              {health?.api_key_configured ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Isolated & Active
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Not Configured
                </span>
              )}
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Your Gemini API key is strictly isolated on the FastAPI backend (
              <code className="font-mono text-[11px]">{health?.api_key_source || "server"}</code>)
              and is never exposed to the browser or client network responses.
            </p>
          </div>

          {/* Theme Preference */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                Appearance Theme
              </p>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Switch between light and dark workspace themes
              </p>
            </div>
            <div className="inline-flex p-1 rounded-xl bg-zinc-100 dark:bg-zinc-800 border border-zinc-200/70 dark:border-zinc-700">
              <button
                type="button"
                onClick={() => handleFieldChange({ theme: "light" })}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  settings.theme === "light"
                    ? "bg-white text-zinc-900 shadow-2xs"
                    : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400"
                }`}
              >
                <Sun className="w-3.5 h-3.5" />
                Light
              </button>
              <button
                type="button"
                onClick={() => handleFieldChange({ theme: "dark" })}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  settings.theme === "dark"
                    ? "bg-zinc-900 text-white shadow-2xs"
                    : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400"
                }`}
              >
                <Moon className="w-3.5 h-3.5" />
                Dark
              </button>
            </div>
          </div>

          {/* Default Gemini Model */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-zinc-900 dark:text-zinc-100">
              Default Gemini Model
            </label>
            <select
              value={settings.default_model}
              onChange={(e) => handleFieldChange({ default_model: e.target.value })}
              className="w-full px-3 py-2 text-xs font-medium rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none"
            >
              {models
                .filter((m) => m.available)
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name} ({m.id})
                  </option>
                ))}
            </select>
          </div>

          {/* Default Retrieval Mode */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-zinc-900 dark:text-zinc-100">
              Default Retrieval Mode
            </label>
            <select
              value={settings.retrieval_mode}
              onChange={(e) =>
                handleFieldChange({ retrieval_mode: e.target.value as RetrievalMode })
              }
              className="w-full px-3 py-2 text-xs font-medium rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none"
            >
              <option value="corrective_rag">
                Corrective RAG (CRAG — Automatic Relevance Grading & Query Rewrite)
              </option>
              <option value="document_search">
                Document Search (Fast Hybrid Vector + Keyword Retrieval)
              </option>
              <option value="compare_documents">
                Compare Documents (Cross-File Diversified Evidence Synthesis)
              </option>
            </select>
          </div>

          {/* Top-K Evidence Chunks */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                Retrieved Evidence Chunks (Top-K)
              </label>
              <span className="text-xs font-mono font-semibold text-blue-600 dark:text-blue-400">
                {settings.top_k} chunks
              </span>
            </div>
            <input
              type="range"
              min={2}
              max={12}
              step={1}
              value={settings.top_k}
              onChange={(e) => handleFieldChange({ top_k: parseInt(e.target.value, 10) })}
              className="w-full accent-blue-600"
            />
            <p className="text-[11px] text-zinc-400">
              Controls how many ranked passages are passed to the model per turn.
            </p>
          </div>

          {/* CRAG Relevance Threshold */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                CRAG Relevance Threshold
              </label>
              <span className="text-xs font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                {Number(settings.crag_threshold).toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={0.1}
              max={0.5}
              step={0.02}
              value={settings.crag_threshold}
              onChange={(e) =>
                handleFieldChange({ crag_threshold: parseFloat(e.target.value) })
              }
              className="w-full accent-emerald-600"
            />
            <p className="text-[11px] text-zinc-400">
              Minimum hybrid relevance score before Corrective RAG triggers query expansion.
            </p>
          </div>

          {/* Danger Zone: Clear Conversation History */}
          <div className="pt-4 border-t border-zinc-200/80 dark:border-zinc-800 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-rose-600 dark:text-rose-400">
                Clear Conversation History
              </p>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Deletes all saved chat threads (uploaded documents remain intact)
              </p>
            </div>

            {confirmClear ? (
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={async () => {
                    await onClearAllConversations();
                    setConfirmClear(false);
                    onClose();
                  }}
                  className="px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
                >
                  Confirm Clear
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmClear(false)}
                  className="px-2.5 py-1.5 rounded-xl bg-zinc-200 dark:bg-zinc-800 text-xs font-medium"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmClear(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-200 dark:border-rose-900/60 text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 text-xs font-medium shrink-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Chats
              </button>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 bg-zinc-50 dark:bg-zinc-950 border-t border-zinc-200/80 dark:border-zinc-800">
          <span className="text-xs text-zinc-400">
            {saving ? "Saving preferences..." : "All changes saved automatically"}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-semibold"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
