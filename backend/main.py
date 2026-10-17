"""
FastAPI Backend Server for NeuralRAG Commercial AI Document Chat Platform.
Provides REST + SSE Streaming APIs for Multi-File Ingestion, Collections,
Hybrid RAG, Corrective RAG (CRAG), Document Comparison, Gemini Model Registry,
Citation Inspection, Conversation Persistence, and User Settings.
"""

import asyncio
from collections import defaultdict
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.config import (
    ALLOWED_EXTENSIONS,
    CRAG_RELEVANCE_THRESHOLD,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_TOP_K,
    MAX_UPLOAD_SIZE_MB,
    RATE_LIMIT_RPM,
    get_server_gemini_api_key,
)
from backend.database import DatabaseManager
from backend.ingestion import (
    ingest_document_bytes,
    save_uploaded_bytes_safely,
    validate_upload_file,
)
from backend.models_registry import gemini_provider
from backend.rag_engine import execute_rag_workflow
from backend.vector_store import vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("neuralrag.api")

app = FastAPI(
    title="NeuralRAG AI Document Intelligence API",
    version="2.0.0",
    description="Commercial Multi-File RAG, Corrective RAG (CRAG), and Gemini Model Registry Backend"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager()

# Simple in-memory sliding-window rate limiter per client IP
_rate_buckets: Dict[str, List[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "local"
    now = time.time()
    window = [t for t in _rate_buckets[client_ip] if now - t < 60.0]
    if len(window) >= RATE_LIMIT_RPM * 4:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please wait a moment before retrying."}
        )
    window.append(now)
    _rate_buckets[client_ip] = window
    return await call_next(request)


# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------
class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=400)


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=160)
    collection_id: str = Field(default="default")
    model_id: str = Field(default=DEFAULT_GEMINI_MODEL)
    retrieval_mode: str = Field(default="corrective_rag")


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=160)
    collection_id: Optional[str] = None
    model_id: Optional[str] = None
    retrieval_mode: Optional[str] = None
    pinned: Optional[bool] = None


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=12000)
    model_id: Optional[str] = None
    retrieval_mode: Optional[str] = None
    collection_id: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=15)
    edit_message_id: Optional[str] = None


class ModelVerifyRequest(BaseModel):
    model_id: str = Field(..., min_length=2, max_length=100)


class SettingsUpdateRequest(BaseModel):
    theme: Optional[str] = None
    default_model: Optional[str] = None
    retrieval_mode: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=15)
    crag_threshold: Optional[float] = Field(default=None, ge=0.05, le=0.8)
    active_collection_id: Optional[str] = None
    response_style: Optional[str] = None


# -----------------------------------------------------------------------------
# 1. Health & Diagnostics Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/health")
def get_health_status():
    api_key, key_source = get_server_gemini_api_key()
    collections = db.list_collections()
    docs = db.list_documents()
    return {
        "status": "healthy",
        "service": "NeuralRAG Backend v2.0",
        "api_key_configured": bool(api_key),
        "api_key_source": key_source if api_key else "Not Configured",
        "default_model": DEFAULT_GEMINI_MODEL,
        "collections_count": len(collections),
        "documents_count": len(docs),
        "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
        "supported_formats": sorted(list(ALLOWED_EXTENSIONS))
    }


# -----------------------------------------------------------------------------
# 2. Gemini Model Registry Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/models")
def list_available_models(verify_live: bool = Query(default=False)):
    models = gemini_provider.list_models(verify_live=verify_live)
    return {
        "provider": gemini_provider.get_provider_name(),
        "default_model": DEFAULT_GEMINI_MODEL,
        "models": models
    }


@app.post("/api/models/verify")
def verify_model_endpoint(req: ModelVerifyRequest):
    result = gemini_provider.verify_single_model(req.model_id)
    return result


# -----------------------------------------------------------------------------
# 3. Document Collections Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/collections")
def get_collections():
    return {"collections": db.list_collections()}


@app.post("/api/collections")
def create_new_collection(req: CollectionCreateRequest):
    col = db.create_collection(name=req.name, description=req.description)
    return col


@app.delete("/api/collections/{collection_id}")
def delete_existing_collection(collection_id: str):
    if collection_id == "default":
        raise HTTPException(status_code=400, detail="The default workspace collection cannot be deleted.")
    docs = db.list_documents(collection_id=collection_id)
    for d in docs:
        try:
            p = Path(d.get("safe_path", ""))
            if p.exists() and p.is_file():
                p.unlink()
        except Exception:
            pass
    deleted = db.delete_collection(collection_id)
    vector_store.invalidate_collection(collection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Collection not found.")
    return {"deleted": True, "collection_id": collection_id}


# -----------------------------------------------------------------------------
# 4. Multi-File Document Upload & Workspace Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/documents")
def list_documents_endpoint(collection_id: Optional[str] = Query(default=None)):
    docs = db.list_documents(collection_id=collection_id)
    return {"documents": docs}


@app.post("/api/documents/upload")
async def upload_documents_endpoint(
    collection_id: str = Form(default="default"),
    files: List[UploadFile] = File(...)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    results: List[Dict[str, Any]] = []

    for upload in files:
        raw_filename = upload.filename or "document.txt"
        file_bytes = await upload.read()
        file_size = len(file_bytes)

        is_valid, safe_name, validation_msg = validate_upload_file(raw_filename, file_size)
        if not is_valid:
            results.append({
                "filename": raw_filename,
                "status": "error",
                "error_message": validation_msg
            })
            continue

        ext = Path(safe_name).suffix.lower().lstrip(".")
        doc_record = db.create_document(
            collection_id=collection_id,
            filename=safe_name,
            safe_path="",
            file_type=ext.upper(),
            file_size=file_size,
            status="processing"
        )
        doc_id = doc_record["id"]

        try:
            saved_path = save_uploaded_bytes_safely(collection_id, doc_id, safe_name, file_bytes)
            chunks, parse_meta = ingest_document_bytes(
                document_id=doc_id,
                filename=safe_name,
                file_bytes=file_bytes
            )

            if not chunks:
                updated = db.update_document_status(
                    doc_id=doc_id,
                    status="error",
                    error_message="No readable text or structured content could be extracted from this file.",
                    metadata=parse_meta
                )
                results.append(updated)
                continue

            db.save_chunks(document_id=doc_id, collection_id=collection_id, chunks=chunks)
            with db._get_conn() as conn:
                conn.execute("UPDATE documents SET safe_path = ? WHERE id = ?", (str(saved_path), doc_id))

            updated = db.update_document_status(
                doc_id=doc_id,
                status="indexed",
                page_count=parse_meta.get("total_pages", 1),
                chunk_count=len(chunks),
                error_message="",
                metadata=parse_meta
            )
            results.append(updated)

        except Exception as exc:
            logger.exception("Error processing uploaded document %s", safe_name)
            updated = db.update_document_status(
                doc_id=doc_id,
                status="error",
                error_message=str(exc)
            )
            results.append(updated)

    # Rebuild persistent hybrid vector index for the collection
    all_col_chunks = db.get_chunks_by_collection(collection_id)
    vector_store.build_or_update_collection_index(collection_id, all_col_chunks)

    return {
        "collection_id": collection_id,
        "uploaded": results,
        "total_collection_chunks": len(all_col_chunks)
    }


@app.get("/api/documents/{doc_id}")
def get_document_details(doc_id: str):
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    chunks = db.get_chunks_by_document(doc_id)
    return {
        "document": doc,
        "chunks": chunks
    }


@app.post("/api/documents/{doc_id}/reindex")
def reindex_document_endpoint(doc_id: str):
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    safe_path = Path(doc.get("safe_path", ""))
    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=400, detail="Source file is no longer available on disk for re-indexing.")

    try:
        file_bytes = safe_path.read_bytes()
        chunks, parse_meta = ingest_document_bytes(
            document_id=doc_id,
            filename=doc["filename"],
            file_bytes=file_bytes
        )
        db.save_chunks(document_id=doc_id, collection_id=doc["collection_id"], chunks=chunks)
        updated = db.update_document_status(
            doc_id=doc_id,
            status="indexed",
            page_count=parse_meta.get("total_pages", 1),
            chunk_count=len(chunks),
            error_message="",
            metadata=parse_meta
        )
        all_col_chunks = db.get_chunks_by_collection(doc["collection_id"])
        vector_store.build_or_update_collection_index(doc["collection_id"], all_col_chunks)
        return {"document": updated, "reindexed_chunks": len(chunks)}
    except Exception as exc:
        db.update_document_status(doc_id=doc_id, status="error", error_message=str(exc))
        raise HTTPException(status_code=500, detail=f"Re-indexing failed: {str(exc)}")


@app.delete("/api/documents/{doc_id}")
def delete_document_endpoint(doc_id: str):
    doc = db.delete_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    safe_path = doc.get("safe_path", "")
    if safe_path:
        try:
            p = Path(safe_path)
            if p.exists() and p.is_file():
                p.unlink()
        except Exception:
            pass

    col_id = doc["collection_id"]
    remaining_chunks = db.get_chunks_by_collection(col_id)
    vector_store.build_or_update_collection_index(col_id, remaining_chunks)
    return {
        "deleted": True,
        "document_id": doc_id,
        "collection_id": col_id,
        "remaining_chunks": len(remaining_chunks)
    }


@app.get("/api/chunks/{chunk_id}")
def get_chunk_citation_details(chunk_id: str):
    chunk = db.get_chunk_by_id(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Cited chunk not found.")
    doc = db.get_document(chunk["document_id"])
    sibling_chunks = db.get_chunks_by_document(chunk["document_id"])
    return {
        "chunk": chunk,
        "document": doc,
        "document_chunks": sibling_chunks
    }


# -----------------------------------------------------------------------------
# 5. Conversations & Chat Endpoints (REST + Streaming SSE)
# -----------------------------------------------------------------------------
@app.get("/api/conversations")
def list_conversations_endpoint(q: str = Query(default="")):
    return {"conversations": db.list_conversations(search_query=q)}


@app.post("/api/conversations")
def create_conversation_endpoint(req: ConversationCreateRequest):
    allowed, reason = gemini_provider.is_model_allowed(req.model_id)
    model_to_use = req.model_id if allowed else DEFAULT_GEMINI_MODEL
    conv = db.create_conversation(
        title=req.title,
        collection_id=req.collection_id,
        model_id=model_to_use,
        retrieval_mode=req.retrieval_mode
    )
    return conv


@app.get("/api/conversations/{conv_id}")
def get_conversation_endpoint(conv_id: str):
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conv


@app.patch("/api/conversations/{conv_id}")
def update_conversation_endpoint(conv_id: str, req: ConversationUpdateRequest):
    if req.model_id is not None:
        allowed, reason = gemini_provider.is_model_allowed(req.model_id)
        if not allowed:
            raise HTTPException(status_code=400, detail=reason)

    updated = db.update_conversation(
        conv_id=conv_id,
        title=req.title,
        model_id=req.model_id,
        collection_id=req.collection_id,
        retrieval_mode=req.retrieval_mode,
        pinned=req.pinned
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return updated


@app.delete("/api/conversations/{conv_id}")
def delete_conversation_endpoint(conv_id: str):
    ok = db.delete_conversation(conv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True, "conversation_id": conv_id}


@app.delete("/api/conversations")
def clear_all_conversations_endpoint():
    count = db.clear_all_conversations()
    return {"cleared": True, "deleted_count": count}


def _auto_title_from_prompt(prompt: str) -> str:
    clean = " ".join(prompt.strip().split())
    if len(clean) <= 48:
        return clean
    return clean[:45].rstrip() + "..."


@app.post("/api/conversations/{conv_id}/messages")
def send_chat_message_endpoint(conv_id: str, req: ChatMessageRequest):
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # Handle Edit & Resubmit or Retry from a specific message
    if req.edit_message_id:
        db.truncate_messages_from(conv_id, req.edit_message_id)
        conv = db.get_conversation(conv_id)

    model_id = req.model_id or conv["model_id"] or DEFAULT_GEMINI_MODEL
    allowed, reason = gemini_provider.is_model_allowed(model_id)
    if not allowed:
        raise HTTPException(status_code=400, detail=reason)

    retrieval_mode = req.retrieval_mode or conv["retrieval_mode"] or "corrective_rag"
    if retrieval_mode not in ("document_search", "corrective_rag", "compare_documents"):
        raise HTTPException(status_code=400, detail=f"Invalid retrieval mode '{retrieval_mode}'.")

    collection_id = req.collection_id or conv["collection_id"] or "default"
    settings = db.get_settings()
    top_k = req.top_k or settings.get("top_k", DEFAULT_TOP_K)
    crag_threshold = settings.get("crag_threshold", CRAG_RELEVANCE_THRESHOLD)

    # Persist selected model, mode, and collection on the conversation
    new_title = conv["title"]
    if conv["title"] in ("New Chat", "Untitled Chat", "") and len(conv.get("messages", [])) == 0:
        new_title = _auto_title_from_prompt(req.content)

    db.update_conversation(
        conv_id=conv_id,
        title=new_title,
        model_id=model_id,
        collection_id=collection_id,
        retrieval_mode=retrieval_mode
    )

    # Record user message
    user_msg = db.add_message(
        conversation_id=conv_id,
        role="user",
        content=req.content.strip(),
        model_id=model_id,
        retrieval_mode=retrieval_mode
    )

    # Load active collection chunks strictly isolated to collection_id
    col_chunks = db.get_chunks_by_collection(collection_id)

    rag_result = execute_rag_workflow(
        query=req.content.strip(),
        collection_id=collection_id,
        collection_chunks=col_chunks,
        model_id=model_id,
        retrieval_mode=retrieval_mode,
        top_k=top_k,
        crag_threshold=crag_threshold,
        conversation_history=conv.get("messages", [])
    )

    asst_msg = db.add_message(
        conversation_id=conv_id,
        role="assistant",
        content=rag_result["content"],
        model_id=model_id,
        retrieval_mode=retrieval_mode,
        citations=rag_result["citations"],
        crag_trace=rag_result["crag_trace"],
        follow_ups=rag_result["follow_ups"],
        latency_ms=rag_result["latency_ms"]
    )

    updated_conv = db.get_conversation(conv_id)
    return {
        "conversation": updated_conv,
        "user_message": user_msg,
        "assistant_message": asst_msg
    }


@app.post("/api/conversations/{conv_id}/stream")
async def stream_chat_message_endpoint(conv_id: str, req: ChatMessageRequest, request: Request):
    """
    Server-Sent Events (SSE) streaming endpoint.
    Streams real-time CRAG stage events followed by progressive response chunks,
    and respects client disconnection (Stop Generation button).
    """
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    if req.edit_message_id:
        db.truncate_messages_from(conv_id, req.edit_message_id)
        conv = db.get_conversation(conv_id)

    model_id = req.model_id or conv["model_id"] or DEFAULT_GEMINI_MODEL
    allowed, reason = gemini_provider.is_model_allowed(model_id)
    if not allowed:
        raise HTTPException(status_code=400, detail=reason)

    retrieval_mode = req.retrieval_mode or conv["retrieval_mode"] or "corrective_rag"
    collection_id = req.collection_id or conv["collection_id"] or "default"
    settings = db.get_settings()
    top_k = req.top_k or settings.get("top_k", DEFAULT_TOP_K)
    crag_threshold = settings.get("crag_threshold", CRAG_RELEVANCE_THRESHOLD)

    new_title = conv["title"]
    if conv["title"] in ("New Chat", "Untitled Chat", "") and len(conv.get("messages", [])) == 0:
        new_title = _auto_title_from_prompt(req.content)

    db.update_conversation(
        conv_id=conv_id,
        title=new_title,
        model_id=model_id,
        collection_id=collection_id,
        retrieval_mode=retrieval_mode
    )

    user_msg = db.add_message(
        conversation_id=conv_id,
        role="user",
        content=req.content.strip(),
        model_id=model_id,
        retrieval_mode=retrieval_mode
    )

    col_chunks = db.get_chunks_by_collection(collection_id)

    async def event_generator():
        yield f"data: {json.dumps({'type': 'user_message', 'message': user_msg, 'conversation_title': new_title})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'stage': 'retrieving', 'detail': f'Searching collection ({len(col_chunks)} chunks) in {retrieval_mode} mode...'})}\n\n"
        await asyncio.sleep(0.02)

        rag_result = await asyncio.to_thread(
            execute_rag_workflow,
            req.content.strip(),
            collection_id,
            col_chunks,
            model_id,
            retrieval_mode,
            top_k,
            crag_threshold,
            conv.get("messages", [])
        )

        yield f"data: {json.dumps({'type': 'crag_trace', 'crag_trace': rag_result['crag_trace'], 'citations': rag_result['citations']})}\n\n"

        full_text = rag_result["content"]
        # Stream progressive token chunks while checking for client abort (Stop Generation)
        words = re.split(r"(\s+)", full_text)
        accumulated = ""
        step_size = max(3, len(words) // 45)

        for i in range(0, len(words), step_size):
            if await request.is_disconnected():
                logger.info("Client disconnected during stream (Stop Generation) for conv %s", conv_id)
                break
            delta = "".join(words[i:i + step_size])
            accumulated += delta
            yield f"data: {json.dumps({'type': 'token', 'delta': delta})}\n\n"
            await asyncio.sleep(0.012)

        saved_content = accumulated.strip() or full_text
        asst_msg = db.add_message(
            conversation_id=conv_id,
            role="assistant",
            content=saved_content,
            model_id=model_id,
            retrieval_mode=retrieval_mode,
            citations=rag_result["citations"],
            crag_trace=rag_result["crag_trace"],
            follow_ups=rag_result["follow_ups"],
            latency_ms=rag_result["latency_ms"]
        )

        yield f"data: {json.dumps({'type': 'done', 'assistant_message': asst_msg})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# -----------------------------------------------------------------------------
# 6. User Settings Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/settings")
def get_user_settings():
    return db.get_settings()


@app.put("/api/settings")
def update_user_settings(req: SettingsUpdateRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if "default_model" in updates:
        allowed, reason = gemini_provider.is_model_allowed(updates["default_model"])
        if not allowed:
            raise HTTPException(status_code=400, detail=reason)
    return db.update_settings(updates)
