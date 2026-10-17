"""
Persistent Hybrid Vector & Lexical Retrieval Store with Cross-Feature Reranking.
Combines Semantic Character/Subword Vectors + Lexical Word N-Gram Vectors + Exact Entity Reranking,
with optional Dense Neural Embeddings (SentenceTransformers MiniLM).
Persists index artifacts per collection in VECTOR_INDEX_DIR.
"""

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.config import VECTOR_INDEX_DIR

_DENSE_MODEL = None


def _get_optional_dense_model():
    global _DENSE_MODEL
    if _DENSE_MODEL is not None:
        return _DENSE_MODEL
    if os.getenv("EMBEDDING_PROVIDER", "hybrid").lower() == "dense":
        try:
            from sentence_transformers import SentenceTransformer
            _DENSE_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            return _DENSE_MODEL
        except Exception:
            return None
    return None


class HybridVectorStore:
    """
    Manages persistent per-collection vector indexes and performs
    Hybrid Retrieval (Vector + Keyword) followed by Cross-Feature Reranking.
    """

    def __init__(self, index_dir: Optional[Path] = None):
        self.index_dir = Path(index_dir) if index_dir else VECTOR_INDEX_DIR
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    def _index_meta_path(self, collection_id: str) -> Path:
        safe_col = re.sub(r"[^a-zA-Z0-9_\-]", "", collection_id) or "default"
        return self.index_dir / f"{safe_col}_index.json"

    def build_or_update_collection_index(self, collection_id: str, chunks: List[Dict[str, Any]]) -> None:
        """Builds and persists the hybrid index for a document collection."""
        meta_path = self._index_meta_path(collection_id)
        if not chunks:
            self._memory_cache.pop(collection_id, None)
            if meta_path.exists():
                try:
                    meta_path.unlink()
                except Exception:
                    pass
            return

        texts = [
            f"{c.get('filename', '')} {c.get('heading', '')} {c.get('sheet_name', '')} {c.get('text', '')}"
            for c in chunks
        ]

        # 1. Lexical Word N-Gram Vectorizer (BM25-like sublinear TF scaling)
        word_vec = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=25000
        )
        try:
            word_matrix = word_vec.fit_transform(texts)
        except ValueError:
            word_vec = TfidfVectorizer(ngram_range=(1, 1))
            word_matrix = word_vec.fit_transform(texts)

        # 2. Subword / Morphological Semantic Vectorizer (captures stems, partials, numbers, identifiers)
        char_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            sublinear_tf=True,
            max_features=25000
        )
        char_matrix = char_vec.fit_transform(texts)

        # 3. Optional Dense Neural Embeddings
        dense_model = _get_optional_dense_model()
        dense_vectors = None
        if dense_model is not None:
            try:
                dense_vectors = dense_model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
            except Exception:
                dense_vectors = None

        self._memory_cache[collection_id] = {
            "chunks": chunks,
            "word_vec": word_vec,
            "word_matrix": word_matrix,
            "char_vec": char_vec,
            "char_matrix": char_matrix,
            "dense_vectors": dense_vectors
        }

        # Persist lightweight snapshot metadata to disk
        snapshot = {
            "collection_id": collection_id,
            "chunk_count": len(chunks),
            "chunk_ids": [c["id"] for c in chunks]
        }
        meta_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    def invalidate_collection(self, collection_id: str) -> None:
        self._memory_cache.pop(collection_id, None)
        meta_path = self._index_meta_path(collection_id)
        if meta_path.exists():
            try:
                meta_path.unlink()
            except Exception:
                pass

    @staticmethod
    def _compute_rerank_bonus(query: str, chunk: Dict[str, Any]) -> float:
        """
        Reranker scoring: boosts chunks with exact phrase matches, numerical/code matches,
        and heading/filename alignment.
        """
        q_lower = query.lower().strip()
        text_lower = chunk.get("text", "").lower()
        heading_lower = chunk.get("heading", "").lower()

        q_tokens = [t for t in re.findall(r"\w+", q_lower) if len(t) > 2 and t not in {
            "what", "where", "when", "which", "who", "whom", "whose", "why", "how",
            "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
            "can", "you", "tell", "explain", "summarize", "compare", "document", "documents", "file", "files"
        }]
        if not q_tokens:
            return 0.0

        matched = sum(1 for tok in q_tokens if tok in text_lower or tok in heading_lower)
        coverage = matched / len(q_tokens)

        bonus = coverage * 0.20
        if len(q_lower) > 8 and q_lower in text_lower:
            bonus += 0.15
        if any(tok in heading_lower for tok in q_tokens):
            bonus += 0.08
        return bonus

    def search(
        self,
        collection_id: str,
        chunks: List[Dict[str, Any]],
        query: str,
        top_k: int = 5,
        rerank: bool = True,
        diversify_files: bool = False
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Executes Hybrid Search (Vector + Keyword) and optional Cross-Feature Reranking.
        When diversify_files=True (used in Compare Documents mode), ensures balanced
        representation across all uploaded files in the collection.
        """
        if not chunks or not query or not query.strip():
            return []

        cached = self._memory_cache.get(collection_id)
        if not cached or len(cached.get("chunks", [])) != len(chunks):
            self.build_or_update_collection_index(collection_id, chunks)
            cached = self._memory_cache.get(collection_id)

        if not cached:
            return []

        word_vec = cached["word_vec"]
        word_matrix = cached["word_matrix"]
        char_vec = cached["char_vec"]
        char_matrix = cached["char_matrix"]
        dense_vectors = cached.get("dense_vectors")

        q_word = word_vec.transform([query])
        word_scores = cosine_similarity(q_word, word_matrix)[0]

        q_char = char_vec.transform([query])
        char_scores = cosine_similarity(q_char, char_matrix)[0]

        if dense_vectors is not None and _get_optional_dense_model() is not None:
            q_dense = _get_optional_dense_model().encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
            dense_scores = dense_vectors @ q_dense
            hybrid_scores = 0.45 * dense_scores + 0.35 * word_scores + 0.20 * char_scores
        else:
            hybrid_scores = 0.60 * word_scores + 0.40 * char_scores

        scored_items: List[Tuple[Dict[str, Any], float]] = []
        for idx, ch in enumerate(chunks):
            base_score = float(hybrid_scores[idx])
            if rerank:
                base_score += self._compute_rerank_bonus(query, ch)
            scored_items.append((ch, min(1.0, round(base_score, 4))))

        scored_items.sort(key=lambda x: x[1], reverse=True)

        if diversify_files:
            # Ensure every distinct document in the collection contributes its top chunks
            by_doc: Dict[str, List[Tuple[Dict[str, Any], float]]] = {}
            for ch, sc in scored_items:
                by_doc.setdefault(ch["document_id"], []).append((ch, sc))

            diversified: List[Tuple[Dict[str, Any], float]] = []
            round_idx = 0
            while len(diversified) < top_k:
                added_in_round = False
                for doc_id, doc_items in by_doc.items():
                    if round_idx < len(doc_items) and len(diversified) < top_k:
                        diversified.append(doc_items[round_idx])
                        added_in_round = True
                if not added_in_round:
                    break
                round_idx += 1
            return diversified

        return scored_items[:min(top_k, len(scored_items))]


# Singleton vector store instance
vector_store = HybridVectorStore()
