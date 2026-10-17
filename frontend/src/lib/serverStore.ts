import {
  Citation,
  Collection,
  Conversation,
  CragTrace,
  DocumentItem,
  ModelInfo,
  RetrievalMode,
  UserSettings,
} from "@/types/api";

export interface StoredChunk {
  id: string;
  document_id: string;
  conversation_id?: string;
  filename: string;
  page_number: number;
  heading: string;
  location_label: string;
  text: string;
  tokens: string[];
}

export interface ServerState {
  collections: Collection[];
  documents: DocumentItem[];
  chunks: StoredChunk[];
  conversations: Conversation[];
  settings: UserSettings;
}

declare global {
  // eslint-disable-next-line no-var
  var __neuralrag_server_state: ServerState | undefined;
}

export function getServerState(): ServerState {
  if (!global.__neuralrag_server_state) {
    global.__neuralrag_server_state = {
      collections: [
        {
          id: "default",
          name: "General Workspace",
          description: "Default multi-file workspace for document intelligence",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      documents: [],
      chunks: [],
      conversations: [],
      settings: {
        theme: "dark",
        default_model: "gemini-3.1-flash-lite",
        retrieval_mode: "corrective_rag",
        top_k: 5,
        crag_threshold: 0.22,
        active_collection_id: "default",
        response_style: "comprehensive",
      },
    };
  }
  return global.__neuralrag_server_state;
}

export const SUPPORTED_MODELS: ModelInfo[] = [
  {
    id: "gemini-3.1-flash-lite",
    display_name: "Gemini 3.1 Flash Lite",
    provider: "google",
    tier: "flash",
    description: "Ultra-fast response latency optimized for dense multi-file extraction.",
    capabilities: ["Document Q&A", "Hybrid Search", "Low Latency"],
    context_window: "1,048,576 tokens",
    recommended_for: "Everyday document inquiries",
    is_default: true,
    available: true,
    verification_status: "verified",
    status_message: "Active & Ready",
  },
  {
    id: "gemini-3.5-flash-lite",
    display_name: "Gemini 3.5 Flash Lite",
    provider: "google",
    tier: "flash",
    description: "High-throughput model with enhanced tabular reasoning.",
    capabilities: ["Tabular Extraction", "Spreadsheets", "Speed"],
    context_window: "1,048,576 tokens",
    recommended_for: "Spreadsheets & CSV analytics",
    is_default: false,
    available: true,
    verification_status: "verified",
    status_message: "Active & Ready",
  },
  {
    id: "gemini-3.5-flash",
    display_name: "Gemini 3.5 Flash",
    provider: "google",
    tier: "flash",
    description: "Premier multimodal workhorse for complex documents and charts.",
    capabilities: ["Multimodal OCR", "Cross-File Synthesis", "Charts"],
    context_window: "1,048,576 tokens",
    recommended_for: "Complex PDFs & scanned documents",
    is_default: false,
    available: true,
    verification_status: "verified",
    status_message: "Active & Ready",
  },
  {
    id: "gemini-3.1-pro-preview",
    display_name: "Gemini 3.1 Pro Preview",
    provider: "google",
    tier: "pro",
    description: "Maximum reasoning depth for multi-document audits and discrepancies.",
    capabilities: ["Deep Reasoning", "Code Extraction", "Document Audits"],
    context_window: "2,097,152 tokens",
    recommended_for: "Deep research & comparative analysis",
    is_default: false,
    available: true,
    verification_status: "verified",
    status_message: "Active & Ready",
  },
];

export function getGeminiApiKey(): string {
  return (
    process.env.GEMINI_API_KEY ||
    process.env.NEXT_PUBLIC_GEMINI_API_KEY ||
    ""
  ).trim();
}

export function tokenize(text: string): string[] {
  const stops = new Set([
    "a", "an", "the", "in", "on", "of", "to", "for", "with", "about",
    "is", "are", "was", "were", "what", "where", "when", "how", "why",
    "can", "you", "tell", "me", "from", "and", "or", "it", "this", "that"
  ]);
  return (text.toLowerCase().match(/\b[a-z0-9]{2,}\b/g) || []).filter(
    (w) => !stops.has(w)
  );
}

export function computeSimilarity(queryTokens: string[], chunkTokens: string[]): number {
  if (queryTokens.length === 0 || chunkTokens.length === 0) return 0;
  const chunkSet = new Set(chunkTokens);
  let matches = 0;
  for (const t of queryTokens) {
    if (chunkSet.has(t)) matches++;
  }
  const jaccard = matches / (queryTokens.length + chunkSet.size - matches);
  const coverage = matches / queryTokens.length;
  return Number((jaccard * 0.4 + coverage * 0.6).toFixed(4));
}

/**
 * Detects if the user query is explicitly targeting a specific filename or file reference.
 */
export function detectTargetFile(query: string, availableFilenames: string[]): string | null {
  const qLower = query.toLowerCase();

  // 1. Direct filename or partial name match
  for (const fname of availableFilenames) {
    const base = fname.toLowerCase();
    const stem = base.replace(/\.[a-z0-9]+$/i, "");
    if (qLower.includes(base) || qLower.includes(stem)) {
      return fname;
    }

    // Check individual significant words in the filename (e.g. "huawei", "registration", "proposal")
    const stemTokens = stem.split(/[^a-z0-9]+/i).filter((t) => t.length > 3);
    const matches = stemTokens.filter((t) => qLower.includes(t));
    if (stemTokens.length > 0 && matches.length >= Math.min(2, stemTokens.length)) {
      return fname;
    }
  }

  // 2. Ordinal file reference (e.g. "first file", "file 1", "second file", "file 2")
  if (availableFilenames.length >= 1) {
    if (qLower.includes("first file") || qLower.includes("file 1") || qLower.includes("doc 1")) {
      return availableFilenames[0];
    }
  }
  if (availableFilenames.length >= 2) {
    if (qLower.includes("second file") || qLower.includes("file 2") || qLower.includes("doc 2")) {
      return availableFilenames[1];
    }
  }
  if (availableFilenames.length >= 3) {
    if (qLower.includes("third file") || qLower.includes("file 3") || qLower.includes("doc 3")) {
      return availableFilenames[2];
    }
  }

  return null;
}

/**
 * Checks if the user is asking for an overview or summary of the documents.
 */
export function isSummaryIntent(query: string): boolean {
  const q = query.toLowerCase();
  const summaryTriggers = [
    "summarize",
    "summary",
    "overview",
    "what is this document about",
    "what is this file about",
    "explain this file",
    "explain this document",
    "key points",
    "key findings",
    "main points",
    "walk me through",
    "tell me about this",
    "give me a summary",
    "what does this document do",
  ];
  return summaryTriggers.some((t) => q.includes(t));
}

/**
 * Samples representative chunks across an entire document (start, middle, sections, tables, end)
 * so that summarization has full document coverage instead of only Page 1.
 */
export function sampleDocumentChunksForSummary(
  chunks: StoredChunk[],
  maxChunks: number = 6
): Array<{ chunk: StoredChunk; score: number }> {
  if (chunks.length <= maxChunks) {
    return chunks.map((c) => ({ chunk: c, score: 0.95 }));
  }

  const result: Array<{ chunk: StoredChunk; score: number }> = [];
  // 1. Always take the first chunk (Intro/Title)
  result.push({ chunk: chunks[0], score: 1.0 });

  // 2. Take evenly distributed chunks across the rest of the document
  const step = (chunks.length - 1) / (maxChunks - 1);
  for (let i = 1; i < maxChunks - 1; i++) {
    const idx = Math.min(chunks.length - 2, Math.floor(i * step));
    result.push({ chunk: chunks[idx], score: 0.9 });
  }

  // 3. Always take the last chunk (Conclusion/Notes)
  result.push({ chunk: chunks[chunks.length - 1], score: 0.85 });

  return result;
}

/**
 * Advanced Multi-File Search with File Targeting and Broad Summary Sampling.
 */
export function searchChunks(
  query: string,
  chunks: StoredChunk[],
  topK: number = 5
): Array<{ chunk: StoredChunk; score: number }> {
  if (chunks.length === 0) return [];

  // Extract available filenames
  const availableFiles = Array.from(new Set(chunks.map((c) => c.filename)));
  const targetFile = detectTargetFile(query, availableFiles);

  // If a specific file is targeted, focus exclusively on that file
  const candidateChunks = targetFile
    ? chunks.filter((c) => c.filename === targetFile)
    : chunks;

  // If this is a summary inquiry, use multi-page broad sampling
  if (isSummaryIntent(query)) {
    if (targetFile) {
      return sampleDocumentChunksForSummary(candidateChunks, topK);
    } else {
      // If no file specified, sample across all available files evenly
      const perFileChunks = Math.max(2, Math.floor(topK / availableFiles.length));
      const combined: Array<{ chunk: StoredChunk; score: number }> = [];
      for (const fname of availableFiles) {
        const fileChunks = chunks.filter((c) => c.filename === fname);
        combined.push(...sampleDocumentChunksForSummary(fileChunks, perFileChunks));
      }
      return combined.slice(0, topK + 2);
    }
  }

  // Standard hybrid relevance scoring
  const qTokens = tokenize(query);
  const scored = candidateChunks.map((c) => ({
    chunk: c,
    score: computeSimilarity(qTokens, c.tokens),
  }));

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK);
}

export function expandQueryForCrag(query: string): string[] {
  const words = tokenize(query);
  if (words.length === 0) return [];
  const rewrites: string[] = [words.join(" ")];
  const expanded: string[] = [...words];

  for (const w of words) {
    if (["revenue", "sales", "profit", "margin", "income"].includes(w)) {
      expanded.push("financial", "growth", "total", "table");
    } else if (["method", "algorithm", "architecture", "system"].includes(w)) {
      expanded.push("model", "design", "technique", "pipeline");
    } else if (["result", "finding", "conclusion"].includes(w)) {
      expanded.push("summary", "metric", "evaluation", "outcome");
    }
  }

  const unique = Array.from(new Set(expanded)).join(" ");
  if (unique !== query.trim()) {
    rewrites.push(unique);
  }
  return rewrites.slice(0, 2);
}
