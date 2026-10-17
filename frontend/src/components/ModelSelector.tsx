"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  Cpu,
  Loader2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { ModelInfo } from "@/types/api";
import { verifySingleModel } from "@/lib/api";

interface ModelSelectorProps {
  models: ModelInfo[];
  selectedModelId: string;
  onSelectModel: (modelId: string) => void;
  onRefreshModels: (verifyLive?: boolean) => Promise<void>;
  disabled?: boolean;
}

export default function ModelSelector({
  models,
  selectedModelId,
  onSelectModel,
  onRefreshModels,
  disabled = false,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeModel =
    models.find((m) => m.id === selectedModelId) ||
    models.find((m) => m.is_default) ||
    models[0];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const handleVerifyClick = async (e: React.MouseEvent, modelId: string) => {
    e.stopPropagation();
    setVerifyingId(modelId);
    try {
      await verifySingleModel(modelId);
      await onRefreshModels(false);
    } catch {
      // handled in UI status
    } finally {
      setVerifyingId(null);
    }
  };

  const handleRefreshCatalog = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setRefreshing(true);
    try {
      await onRefreshModels(true);
    } finally {
      setRefreshing(false);
    }
  };

  const getTierIcon = (tier?: string) => {
    if (tier === "Reasoning" || tier === "Pro") {
      return <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />;
    }
    if (tier === "Balanced") {
      return <Cpu className="w-4 h-4 text-blue-500 shrink-0" />;
    }
    return <Zap className="w-4 h-4 text-emerald-500 shrink-0" />;
  };

  const renderStatusBadge = (model: ModelInfo) => {
    if (model.verification_status === "verified") {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <ShieldCheck className="w-3 h-3" />
          Verified {model.latency_ms ? `${model.latency_ms}ms` : ""}
        </span>
      );
    }
    if (model.verification_status === "verified_in_catalog") {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
          Catalog Active
        </span>
      );
    }
    if (model.verification_status === "configured") {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border border-zinc-500/20">
          Configured
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
        <ShieldAlert className="w-3 h-3" />
        Unavailable
      </span>
    );
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="group inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm font-medium text-zinc-800 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800/80 border border-transparent hover:border-zinc-200/80 dark:hover:border-zinc-700/70 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:opacity-50"
      >
        {getTierIcon(activeModel?.tier)}
        <span className="truncate max-w-[170px] sm:max-w-[220px]">
          {activeModel ? activeModel.display_name : selectedModelId}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-zinc-400 transition-transform duration-150 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-0 mt-2 w-[340px] sm:w-[390px] rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/90 dark:border-zinc-800 shadow-xl shadow-black/10 dark:shadow-black/40 z-50 overflow-hidden animate-in fade-in slide-in-from-top-1 duration-150"
        >
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-100 dark:border-zinc-800/80 bg-zinc-50/60 dark:bg-zinc-900/60">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                Gemini Model Registry
              </p>
              <p className="text-[11px] text-zinc-400 dark:text-zinc-500">
                Server-managed API credentials • Live availability
              </p>
            </div>
            <button
              type="button"
              onClick={handleRefreshCatalog}
              disabled={refreshing}
              title="Refresh live model catalog from server"
              className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="max-h-[380px] overflow-y-auto divide-y divide-zinc-100 dark:divide-zinc-800/60 p-1.5">
            {models.map((model) => {
              const isSelected = model.id === selectedModelId;
              const isVerifying = verifyingId === model.id;

              return (
                <div
                  key={model.id}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    if (!model.available) return;
                    onSelectModel(model.id);
                    setOpen(false);
                  }}
                  className={`relative flex flex-col gap-1.5 p-3 rounded-xl transition-colors ${
                    !model.available
                      ? "opacity-60 cursor-not-allowed bg-zinc-50/40 dark:bg-zinc-900/30"
                      : isSelected
                      ? "bg-blue-50/70 dark:bg-blue-950/30 cursor-pointer"
                      : "hover:bg-zinc-100/80 dark:hover:bg-zinc-800/60 cursor-pointer"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      {getTierIcon(model.tier)}
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                            {model.display_name}
                          </span>
                          {model.is_default && (
                            <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-zinc-200/80 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                              Default
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] font-mono text-zinc-400 dark:text-zinc-500 truncate">
                          {model.id}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {renderStatusBadge(model)}
                      {isSelected && (
                        <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center">
                          <Check className="w-3 h-3 stroke-[2.5]" />
                        </div>
                      )}
                    </div>
                  </div>

                  <p className="text-xs text-zinc-600 dark:text-zinc-300 leading-relaxed">
                    {model.description}
                  </p>

                  <div className="flex items-center justify-between gap-2 pt-1">
                    <div className="flex flex-wrap gap-1">
                      {model.capabilities?.slice(0, 3).map((cap) => (
                        <span
                          key={cap}
                          className="px-1.5 py-0.5 text-[10px] rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
                        >
                          {cap}
                        </span>
                      ))}
                      {model.context_window && (
                        <span className="px-1.5 py-0.5 text-[10px] rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
                          {model.context_window}
                        </span>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={(e) => handleVerifyClick(e, model.id)}
                      disabled={isVerifying}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-100/60 dark:hover:bg-blue-900/30 transition-colors shrink-0"
                    >
                      {isVerifying ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Testing...
                        </>
                      ) : (
                        "Verify Ping"
                      )}
                    </button>
                  </div>

                  {!model.available && model.status_message && (
                    <p className="text-[11px] text-rose-500 dark:text-rose-400 mt-0.5">
                      {model.status_message}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
