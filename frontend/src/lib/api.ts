import {
  ChatMessage,
  ChunkDetailResponse,
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

const API_BASE = "";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      errorDetail = data.detail || data.message || errorDetail;
    } catch {
      const text = await res.text();
      if (text) errorDetail = text;
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
  return handleResponse<HealthStatus>(res);
}

export async function fetchModels(verifyLive = false): Promise<{
  provider: string;
  default_model: string;
  models: ModelInfo[];
}> {
  const res = await fetch(`${API_BASE}/api/models?verify_live=${verifyLive}`, {
    cache: "no-store",
  });
  return handleResponse(res);
}

export async function verifySingleModel(modelId: string): Promise<{
  model_id: string;
  verified: boolean;
  status: string;
  latency_ms: number;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/api/models/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
  return handleResponse(res);
}

export async function fetchCollections(): Promise<{ collections: Collection[] }> {
  const res = await fetch(`${API_BASE}/api/collections`, { cache: "no-store" });
  return handleResponse(res);
}

export async function createCollection(name: string, description = ""): Promise<Collection> {
  const res = await fetch(`${API_BASE}/api/collections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  return handleResponse(res);
}

export async function deleteCollection(collectionId: string): Promise<{ deleted: boolean }> {
  const res = await fetch(`${API_BASE}/api/collections/${collectionId}`, {
    method: "DELETE",
  });
  return handleResponse(res);
}

export async function fetchDocuments(
  collectionId?: string,
  conversationId?: string | null
): Promise<{ documents: DocumentItem[] }> {
  const params = new URLSearchParams();
  if (collectionId) params.set("collection_id", collectionId);
  if (conversationId) params.set("conversation_id", conversationId);
  const qs = params.toString();
  const url = qs ? `${API_BASE}/api/documents?${qs}` : `${API_BASE}/api/documents`;
  const res = await fetch(url, { cache: "no-store" });
  return handleResponse(res);
}

export async function uploadDocuments(
  collectionId: string,
  files: File[],
  conversationId?: string | null
): Promise<{
  collection_id: string;
  uploaded: DocumentItem[];
  total_collection_chunks: number;
}> {
  const formData = new FormData();
  formData.append("collection_id", collectionId);
  if (conversationId) formData.append("conversation_id", conversationId);
  for (const file of files) {
    formData.append("files", file);
  }
  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(res);
}

export async function reindexDocument(docId: string): Promise<{
  document: DocumentItem;
  reindexed_chunks: number;
}> {
  const res = await fetch(`${API_BASE}/api/documents/${docId}/reindex`, {
    method: "POST",
  });
  return handleResponse(res);
}

export async function deleteDocument(docId: string): Promise<{
  deleted: boolean;
  document_id: string;
  remaining_chunks: number;
}> {
  const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
    method: "DELETE",
  });
  return handleResponse(res);
}

export async function fetchChunkDetails(chunkId: string): Promise<ChunkDetailResponse> {
  const res = await fetch(`${API_BASE}/api/chunks/${chunkId}`, { cache: "no-store" });
  return handleResponse(res);
}

export async function fetchConversations(searchQuery = ""): Promise<{ conversations: Conversation[] }> {
  const url = searchQuery
    ? `${API_BASE}/api/conversations?q=${encodeURIComponent(searchQuery)}`
    : `${API_BASE}/api/conversations`;
  const res = await fetch(url, { cache: "no-store" });
  return handleResponse(res);
}

export async function createConversation(params: {
  title?: string;
  collection_id?: string;
  model_id?: string;
  retrieval_mode?: RetrievalMode;
}): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/api/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return handleResponse(res);
}

export async function fetchConversation(convId: string): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/api/conversations/${convId}`, { cache: "no-store" });
  return handleResponse(res);
}

export async function updateConversation(
  convId: string,
  updates: {
    title?: string;
    collection_id?: string;
    model_id?: string;
    retrieval_mode?: RetrievalMode;
    pinned?: boolean;
  }
): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/api/conversations/${convId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  return handleResponse(res);
}

export async function deleteConversation(convId: string): Promise<{ deleted: boolean }> {
  const res = await fetch(`${API_BASE}/api/conversations/${convId}`, {
    method: "DELETE",
  });
  return handleResponse(res);
}

export async function clearAllConversations(): Promise<{ cleared: boolean; deleted_count: number }> {
  const res = await fetch(`${API_BASE}/api/conversations`, {
    method: "DELETE",
  });
  return handleResponse(res);
}

export async function fetchSettings(): Promise<UserSettings> {
  const res = await fetch(`${API_BASE}/api/settings`, { cache: "no-store" });
  return handleResponse(res);
}

export async function updateSettings(updates: Partial<UserSettings>): Promise<UserSettings> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  return handleResponse(res);
}

export interface StreamCallbacks {
  onUserMessage?: (msg: ChatMessage, newTitle: string) => void;
  onStatus?: (stage: string, detail: string) => void;
  onCragTrace?: (trace: CragTrace, citations: Citation[]) => void;
  onToken?: (delta: string) => void;
  onDone?: (assistantMessage: ChatMessage) => void;
}

export async function streamChatMessage(
  convId: string,
  payload: {
    content: string;
    model_id?: string;
    retrieval_mode?: RetrievalMode;
    collection_id?: string;
    top_k?: number;
    edit_message_id?: string;
  },
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/conversations/${convId}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      errorDetail = data.detail || data.message || errorDetail;
    } catch {
      const text = await res.text();
      if (text) errorDetail = text;
    }
    throw new Error(errorDetail);
  }

  if (!res.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const evt of events) {
      const line = evt.trim();
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.replace(/^data:\s*/, "");
      try {
        const parsed = JSON.parse(jsonStr);
        if (parsed.type === "user_message" && callbacks.onUserMessage) {
          callbacks.onUserMessage(parsed.message, parsed.conversation_title);
        } else if (parsed.type === "status" && callbacks.onStatus) {
          callbacks.onStatus(parsed.stage, parsed.detail);
        } else if (parsed.type === "crag_trace" && callbacks.onCragTrace) {
          callbacks.onCragTrace(parsed.crag_trace, parsed.citations);
        } else if (parsed.type === "token" && callbacks.onToken) {
          callbacks.onToken(parsed.delta);
        } else if (parsed.type === "done" && callbacks.onDone) {
          callbacks.onDone(parsed.assistant_message);
        }
      } catch {
        // Ignore partial JSON frames
      }
    }
  }
}
