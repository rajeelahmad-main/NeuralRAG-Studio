"""
Persistent SQLite Database Layer for NeuralRAG Platform.
Manages Document Collections, Uploaded Documents, Chunks with Source Metadata,
Persistent Conversations, Messages with Citations & CRAG Trace, and User Settings.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import DATABASE_PATH, DEFAULT_GEMINI_MODEL, DEFAULT_TOP_K


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DatabaseManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    safe_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'processing',
                    error_message TEXT DEFAULT '',
                    page_count INTEGER DEFAULT 1,
                    chunk_count INTEGER DEFAULT 0,
                    metadata_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    collection_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    page_number INTEGER DEFAULT 1,
                    heading TEXT DEFAULT '',
                    sheet_name TEXT DEFAULT '',
                    row_range TEXT DEFAULT '',
                    char_start INTEGER DEFAULT 0,
                    char_end INTEGER DEFAULT 0,
                    metadata_json TEXT DEFAULT '{}',
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    collection_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    retrieval_mode TEXT NOT NULL DEFAULT 'corrective_rag',
                    pinned INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model_id TEXT DEFAULT '',
                    retrieval_mode TEXT DEFAULT '',
                    citations_json TEXT DEFAULT '[]',
                    crag_trace_json TEXT DEFAULT '{}',
                    follow_ups_json TEXT DEFAULT '[]',
                    latency_ms INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # Ensure default collection exists
            cur = conn.execute("SELECT id FROM collections WHERE id = 'default'")
            if not cur.fetchone():
                now = utc_now_iso()
                conn.execute(
                    "INSERT INTO collections (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    ("default", "General Workspace", "Default multi-document knowledge collection", now, now)
                )

    # -------------------------------------------------------------------------
    # Collections
    # -------------------------------------------------------------------------
    def list_collections(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT c.*,
                       COUNT(DISTINCT d.id) as document_count,
                       COALESCE(SUM(d.chunk_count), 0) as total_chunks
                FROM collections c
                LEFT JOIN documents d ON d.collection_id = c.id
                GROUP BY c.id
                ORDER BY CASE WHEN c.id = 'default' THEN 0 ELSE 1 END, c.updated_at DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def create_collection(self, name: str, description: str = "") -> Dict[str, Any]:
        col_id = f"col_{uuid.uuid4().hex[:10]}"
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO collections (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (col_id, name.strip(), description.strip(), now, now)
            )
        return self.get_collection(col_id)

    def get_collection(self, col_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT c.*,
                       COUNT(DISTINCT d.id) as document_count,
                       COALESCE(SUM(d.chunk_count), 0) as total_chunks
                FROM collections c
                LEFT JOIN documents d ON d.collection_id = c.id
                WHERE c.id = ?
                GROUP BY c.id
            """, (col_id,)).fetchone()
            return dict(row) if row else None

    def delete_collection(self, col_id: str) -> bool:
        if col_id == "default":
            return False
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM collections WHERE id = ?", (col_id,))
            return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Documents & Chunks
    # -------------------------------------------------------------------------
    def create_document(
        self,
        collection_id: str,
        filename: str,
        safe_path: str,
        file_type: str,
        file_size: int,
        status: str = "processing",
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        doc_id = doc_id or f"doc_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with self._get_conn() as conn:
            # Ensure collection exists
            col = conn.execute("SELECT id FROM collections WHERE id = ?", (collection_id,)).fetchone()
            if not col:
                collection_id = "default"
            conn.execute(
                """INSERT INTO documents
                   (id, collection_id, filename, safe_path, file_type, file_size, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, collection_id, filename, safe_path, file_type, file_size, status, now)
            )
            conn.execute("UPDATE collections SET updated_at = ? WHERE id = ?", (now, collection_id))
        return self.get_document(doc_id)

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        page_count: int = 1,
        chunk_count: int = 0,
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE documents
                   SET status = ?, page_count = ?, chunk_count = ?, error_message = ?, metadata_json = ?
                   WHERE id = ?""",
                (status, page_count, chunk_count, error_message, json.dumps(metadata or {}), doc_id)
            )
        return self.get_document(doc_id)

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
            return d

    def list_documents(self, collection_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            if collection_id:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE collection_id = ? ORDER BY created_at DESC",
                    (collection_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                result.append(d)
            return result

    def delete_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        doc = self.get_document(doc_id)
        if not doc:
            return None
        with self._get_conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return doc

    def save_chunks(self, document_id: str, collection_id: str, chunks: List[Dict[str, Any]]) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            for ch in chunks:
                conn.execute(
                    """INSERT INTO chunks
                       (id, document_id, collection_id, chunk_index, text, filename,
                        page_number, heading, sheet_name, row_range, char_start, char_end, metadata_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        ch["id"],
                        document_id,
                        collection_id,
                        ch["chunk_index"],
                        ch["text"],
                        ch["filename"],
                        ch.get("page_number", 1),
                        ch.get("heading", ""),
                        ch.get("sheet_name", ""),
                        ch.get("row_range", ""),
                        ch.get("char_start", 0),
                        ch.get("char_end", 0),
                        json.dumps(ch.get("metadata", {}))
                    )
                )

    def get_chunks_by_collection(self, collection_id: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE collection_id = ? ORDER BY document_id, chunk_index ASC",
                (collection_id,)
            ).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                res.append(d)
            return res

    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC",
                (document_id,)
            ).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                res.append(d)
            return res

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
            return d

    # -------------------------------------------------------------------------
    # Conversations & Messages
    # -------------------------------------------------------------------------
    def create_conversation(
        self,
        title: str = "New Chat",
        collection_id: str = "default",
        model_id: str = DEFAULT_GEMINI_MODEL,
        retrieval_mode: str = "corrective_rag"
    ) -> Dict[str, Any]:
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO conversations
                   (id, title, collection_id, model_id, retrieval_mode, pinned, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
                (conv_id, title.strip() or "New Chat", collection_id, model_id, retrieval_mode, now, now)
            )
        return self.get_conversation(conv_id)

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if not row:
                return None
            c = dict(row)
            c["pinned"] = bool(c["pinned"])
            c["messages"] = self.list_messages(conv_id)
            return c

    def list_conversations(self, search_query: str = "") -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            if search_query and search_query.strip():
                q = f"%{search_query.strip()}%"
                rows = conn.execute("""
                    SELECT DISTINCT c.*
                    FROM conversations c
                    LEFT JOIN messages m ON m.conversation_id = c.id
                    WHERE c.title LIKE ? OR m.content LIKE ?
                    ORDER BY c.pinned DESC, c.updated_at DESC
                """, (q, q)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM conversations
                    ORDER BY pinned DESC, updated_at DESC
                """).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["pinned"] = bool(d["pinned"])
                res.append(d)
            return res

    def update_conversation(
        self,
        conv_id: str,
        title: Optional[str] = None,
        model_id: Optional[str] = None,
        collection_id: Optional[str] = None,
        retrieval_mode: Optional[str] = None,
        pinned: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        conv = self.get_conversation(conv_id)
        if not conv:
            return None
        new_title = title.strip() if title is not None else conv["title"]
        new_model = model_id if model_id is not None else conv["model_id"]
        new_col = collection_id if collection_id is not None else conv["collection_id"]
        new_mode = retrieval_mode if retrieval_mode is not None else conv["retrieval_mode"]
        new_pin = int(pinned) if pinned is not None else int(conv["pinned"])
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE conversations
                   SET title = ?, model_id = ?, collection_id = ?, retrieval_mode = ?, pinned = ?, updated_at = ?
                   WHERE id = ?""",
                (new_title, new_model, new_col, new_mode, new_pin, now, conv_id)
            )
        return self.get_conversation(conv_id)

    def delete_conversation(self, conv_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            return cur.rowcount > 0

    def clear_all_conversations(self) -> int:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM conversations")
            return cur.rowcount

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model_id: str = "",
        retrieval_mode: str = "",
        citations: Optional[List[Dict[str, Any]]] = None,
        crag_trace: Optional[Dict[str, Any]] = None,
        follow_ups: Optional[List[str]] = None,
        latency_ms: int = 0
    ) -> Dict[str, Any]:
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO messages
                   (id, conversation_id, role, content, model_id, retrieval_mode,
                    citations_json, crag_trace_json, follow_ups_json, latency_ms, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    msg_id,
                    conversation_id,
                    role,
                    content,
                    model_id,
                    retrieval_mode,
                    json.dumps(citations or []),
                    json.dumps(crag_trace or {}),
                    json.dumps(follow_ups or []),
                    latency_ms,
                    now
                )
            )
            conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
        return self.get_message(msg_id)

    def get_message(self, msg_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
            if not row:
                return None
            return self._deserialize_message(dict(row))

    def list_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC, rowid ASC",
                (conversation_id,)
            ).fetchall()
            return [self._deserialize_message(dict(r)) for r in rows]

    def truncate_messages_from(self, conversation_id: str, message_id: str) -> bool:
        """Deletes the specified message and any subsequent messages in the conversation (for Edit & Resubmit / Retry)."""
        with self._get_conn() as conn:
            target = conn.execute(
                "SELECT rowid FROM messages WHERE id = ? AND conversation_id = ?",
                (message_id, conversation_id)
            ).fetchone()
            if not target:
                return False
            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ? AND rowid >= ?",
                (conversation_id, target["rowid"])
            )
            return True

    @staticmethod
    def _deserialize_message(d: Dict[str, Any]) -> Dict[str, Any]:
        d["citations"] = json.loads(d.pop("citations_json", "[]") or "[]")
        d["crag_trace"] = json.loads(d.pop("crag_trace_json", "{}") or "{}")
        d["follow_ups"] = json.loads(d.pop("follow_ups_json", "[]") or "[]")
        return d

    # -------------------------------------------------------------------------
    # User Settings
    # -------------------------------------------------------------------------
    def get_settings(self) -> Dict[str, Any]:
        defaults = {
            "theme": "dark",
            "default_model": DEFAULT_GEMINI_MODEL,
            "retrieval_mode": "corrective_rag",
            "top_k": DEFAULT_TOP_K,
            "crag_threshold": 0.22,
            "active_collection_id": "default",
            "response_style": "comprehensive"
        }
        with self._get_conn() as conn:
            rows = conn.execute("SELECT key, value_json FROM settings").fetchall()
            for r in rows:
                try:
                    defaults[r["key"]] = json.loads(r["value_json"])
                except Exception:
                    pass
        return defaults

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        now = utc_now_iso()
        with self._get_conn() as conn:
            for k, v in updates.items():
                conn.execute(
                    """INSERT INTO settings (key, value_json, updated_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at""",
                    (k, json.dumps(v), now)
                )
        return self.get_settings()
