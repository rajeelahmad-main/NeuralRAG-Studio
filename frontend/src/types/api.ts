export type RetrievalMode = "document_search" | "corrective_rag" | "compare_documents";

export interface ModelInfo {
  id: string;
  display_name: string;
  provider: string;
  tier: string;
  description: string;
  capabilities: string[];
  context_window: string;
  recommended_for: string;
  is_default: boolean;
  available: boolean;
  verification_status: "verified" | "verified_in_catalog" | "configured" | "unavailable";
  status_message: string;
  latency_ms?: number;
}

export interface Collection {
  id: string;
  name: string;
  description: string;
  document_count?: number;
  chunk_count?: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  collection_id: string;
  filename: string;
  safe_path: string;
  file_type: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  status: "processing" | "indexed" | "error";
  error_message: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface Citation {
  citation_index: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  heading: string;
  sheet_name: string;
  row_range: string;
  location_label: string;
  score: number;
  relevance_grade: "relevant" | "ambiguous" | "irrelevant";
  excerpt: string;
}

export interface CragTrace {
  mode: RetrievalMode;
  status: string;
  initial_candidates: number;
  relevant_count?: number;
  ambiguous_count?: number;
  rewritten_queries: string[];
  retries_used: number;
  final_evidence_count: number;
  confidence: number;
  llm_ok?: boolean;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  model_id: string;
  retrieval_mode: RetrievalMode;
  citations: Citation[];
  crag_trace: CragTrace;
  follow_ups: string[];
  latency_ms: number;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  collection_id: string;
  model_id: string;
  retrieval_mode: RetrievalMode;
  pinned: boolean;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface UserSettings {
  theme: "light" | "dark";
  default_model: string;
  retrieval_mode: RetrievalMode;
  top_k: number;
  crag_threshold: number;
  active_collection_id: string;
  response_style: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  api_key_configured: boolean;
  api_key_source: string;
  default_model: string;
  collections_count: number;
  documents_count: number;
  max_upload_size_mb: number;
  supported_formats: string[];
}

export interface ChunkDetailResponse {
  chunk: {
    id: string;
    document_id: string;
    collection_id: string;
    chunk_index: number;
    text: string;
    filename: string;
    page_number: number;
    heading: string;
    sheet_name: string;
    row_range: string;
    char_start: number;
    char_end: number;
    metadata: Record<string, any>;
  };
  document: DocumentItem;
  document_chunks: Array<{
    id: string;
    chunk_index: number;
    text: string;
    page_number: number;
    heading: string;
    sheet_name: string;
    row_range: string;
    metadata: Record<string, any>;
  }>;
}
