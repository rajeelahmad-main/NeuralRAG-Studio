import {
  ChatMessage,
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

// Global in-memory server store for Vercel / serverless runtime
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

export function searchChunks(
  query: string,
  chunks: StoredChunk[],
  topK: number = 5
): Array<{ chunk: StoredChunk; score: number }> {
  const qTokens = tokenize(query);
  const scored = chunks.map((c) => ({
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
