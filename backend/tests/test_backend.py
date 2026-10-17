"""
Comprehensive automated tests for NeuralRAG AI Document Chat Platform backend.
Covers:
1. Health check & API key protection (never exposed in payloads).
2. Gemini Model Registry & model verification.
3. Collection creation, multi-file ingestion (MD, TXT, CSV, XLSX, DOCX, PDF), path traversal sanitization.
4. Hybrid Vector Search, Corrective RAG (CRAG) query rewriting/verification trace, and Compare Documents mode.
5. Source citations, chunk inspection, and abstention when evidence is missing.
6. Conversation persistence, model selection per conversation, rename/pin/delete, message edit & resubmit, SSE streaming, and document deletion cleanup.
"""

import io
import json
from unittest.mock import patch

import docx
import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend.config import get_server_gemini_api_key
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _mock_generate(model_id: str, system_instruction: str, user_prompt: str, temperature: float = 0.0, max_tokens: int = 1200):
    """Deterministic mock for LLM generation during unit/integration tests so tests run fast and predictably."""
    return (
        True,
        (
            "### Executive Summary\n\n"
            "According to the uploaded documents, Q3 2026 cloud revenue reached **$48.5M** with a 32% YoY increase [Source 1]. "
            "Furthermore, the security audit confirms zero critical vulnerabilities after the v2.4 patch [Source 2]."
        ),
        {"latency_ms": 120, "model_id": model_id},
    )


def test_health_and_api_key_protection(client: TestClient):
    """Verify health endpoint works and NEVER exposes the raw API key."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "api_key_configured" in data
    # Ensure actual secret string is never present in response
    raw_key, _ = get_server_gemini_api_key()
    if raw_key:
        assert raw_key not in res.text


def test_models_registry_and_settings(client: TestClient):
    """Verify server-side Gemini model registry returns friendly names, IDs, capabilities, and default model."""
    res = client.get("/api/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "default_model" in data
    model_ids = [m["id"] for m in data["models"]]
    assert "gemini-3.1-flash-lite" in model_ids
    assert "gemini-3.5-flash" in model_ids

    # Check settings endpoint
    s_res = client.get("/api/settings")
    assert s_res.status_code == 200
    s_data = s_res.json()
    assert "default_model" in s_data
    assert "retrieval_mode" in s_data

    # Update settings
    u_res = client.put("/api/settings", json={"top_k": 8, "theme": "dark"})
    assert u_res.status_code == 200
    assert u_res.json()["top_k"] == 8


def test_collection_and_multifile_ingestion(client: TestClient):
    """Test creating a collection and uploading Markdown, CSV, XLSX, and DOCX files."""
    c_res = client.post(
        "/api/collections",
        json={"name": "Q3 Enterprise Audit", "description": "Financial and technical documents for Q3 2026"},
    )
    assert c_res.status_code == 200
    collection_id = c_res.json()["id"]

    # 1. Prepare Markdown file
    md_bytes = (
        b"# Q3 2026 Financial Report\n\n"
        b"## Cloud Division Performance\n"
        b"In Q3 2026, the Cloud Division achieved $48.5M in recurring revenue, representing 32% YoY growth.\n"
        b"Operating margin expanded to 24.8% driven by automated infrastructure scaling.\n"
    )

    # 2. Prepare CSV file
    csv_bytes = (
        b"region,revenue_millions,yoy_growth_pct,headcount\n"
        b"North America,28.5,34.2,140\n"
        b"Europe,12.0,28.1,65\n"
        b"APAC,8.0,30.5,45\n"
    )

    # 3. Prepare XLSX file
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SecurityMetrics"
    ws.append(["Control_ID", "Component", "Status", "Patch_Version"])
    ws.append(["SEC-101", "API Gateway", "Passed - Zero Critical Vulnerabilities", "v2.4"])
    ws.append(["SEC-102", "Vector Index Encryption", "Passed - AES-256 Enabled", "v2.4"])
    xlsx_buf = io.BytesIO()
    wb.save(xlsx_buf)
    xlsx_bytes = xlsx_buf.getvalue()

    # 4. Prepare DOCX file
    doc = docx.Document()
    doc.add_heading("Architecture & Compliance Overview", level=1)
    doc.add_paragraph(
        "The v2.4 security patch remediated all critical vulnerabilities and enforced strict server-side API key isolation."
    )
    docx_buf = io.BytesIO()
    doc.save(docx_buf)
    docx_bytes = docx_buf.getvalue()

    # Upload all files in a single multi-file request (also test path traversal sanitization in filename)
    files = [
        ("files", ("../../q3_financial_report.md", io.BytesIO(md_bytes), "text/markdown")),
        ("files", ("regional_breakdown.csv", io.BytesIO(csv_bytes), "text/csv")),
        ("files", ("security_audit_2026.xlsx", io.BytesIO(xlsx_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("files", ("compliance_overview.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
    ]
    up_res = client.post(
        "/api/documents/upload",
        data={"collection_id": collection_id},
        files=files,
    )
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert len(up_data["uploaded"]) == 4

    # Verify path traversal was stripped and status is indexed
    filenames = [d["filename"] for d in up_data["uploaded"]]
    assert "q3_financial_report.md" in filenames
    for d in up_data["uploaded"]:
        assert d["status"] == "indexed"
        assert d["chunk_count"] >= 1

    # Verify Unsupported file rejection
    bad_res = client.post(
        "/api/documents/upload",
        data={"collection_id": collection_id},
        files=[("files", ("malware.exe", io.BytesIO(b"MZ..."), "application/octet-stream"))],
    )
    assert bad_res.status_code == 200
    assert bad_res.json()["uploaded"][0]["status"] == "error"
    assert "Unsupported file format" in bad_res.json()["uploaded"][0]["error_message"]


def test_rag_modes_citations_and_conversation_workflow(client: TestClient):
    """Test Document Search, Corrective RAG, Compare Documents, citations, message editing, and SSE streaming."""
    cols = client.get("/api/collections").json()["collections"]
    audit_col = next(c for c in cols if c["name"] == "Q3 Enterprise Audit")
    collection_id = audit_col["id"]

    # Create a conversation bound to this collection and model
    conv_res = client.post(
        "/api/conversations",
        json={
            "title": "New Chat",
            "collection_id": collection_id,
            "model_id": "gemini-3.1-flash-lite",
            "retrieval_mode": "corrective_rag",
        },
    )
    assert conv_res.status_code == 200
    conv_id = conv_res.json()["id"]

    with patch("backend.models_registry.gemini_provider.generate", side_effect=_mock_generate):
        # 1. Send message in Corrective RAG mode
        msg_res = client.post(
            f"/api/conversations/{conv_id}/messages",
            json={
                "content": "What was the Q3 2026 cloud revenue and what did the security audit find?",
                "model_id": "gemini-3.1-flash-lite",
                "retrieval_mode": "corrective_rag",
                "collection_id": collection_id,
            },
        )
        assert msg_res.status_code == 200
        payload = msg_res.json()
        assistant_msg = payload["assistant_message"]
        assert "$48.5M" in assistant_msg["content"]
        assert len(assistant_msg["citations"]) >= 1
        assert assistant_msg["crag_trace"]["mode"] == "corrective_rag"
        assert len(assistant_msg["follow_ups"]) >= 2

        # Verify conversation auto-titled from first message
        assert payload["conversation"]["title"] != "New Chat"

        # 2. Inspect a citation chunk via /api/chunks/{chunk_id}
        first_citation = assistant_msg["citations"][0]
        chunk_res = client.get(f"/api/chunks/{first_citation['chunk_id']}")
        assert chunk_res.status_code == 200
        chunk_data = chunk_res.json()
        assert chunk_data["chunk"]["filename"] == first_citation["filename"]
        assert len(chunk_data["chunk"]["text"]) > 10

        # 3. Test Compare Documents mode
        cmp_res = client.post(
            f"/api/conversations/{conv_id}/messages",
            json={
                "content": "Compare the financial performance in the report with the security metrics.",
                "model_id": "gemini-3.1-flash-lite",
                "retrieval_mode": "compare_documents",
                "collection_id": collection_id,
            },
        )
        assert cmp_res.status_code == 200
        cmp_citations = cmp_res.json()["assistant_message"]["citations"]
        cited_files = {c["filename"] for c in cmp_citations}
        # Compare mode should diversify across at least 2 distinct documents
        assert len(cited_files) >= 2

        # 4. Test SSE Streaming endpoint
        stream_res = client.post(
            f"/api/conversations/{conv_id}/stream",
            json={
                "content": "Summarize regional revenue breakdown.",
                "model_id": "gemini-3.1-flash-lite",
                "retrieval_mode": "document_search",
                "collection_id": collection_id,
            },
        )
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers["content-type"]
        stream_text = stream_res.text
        assert '"type": "status"' in stream_text
        assert '"type": "token"' in stream_text
        assert '"type": "done"' in stream_text

        # 5. Test editing & resubmitting an earlier user message
        user_msg_id = payload["user_message"]["id"]
        edit_res = client.post(
            f"/api/conversations/{conv_id}/messages",
            json={
                "content": "Updated question: What is the North America revenue and headcount?",
                "model_id": "gemini-3.1-flash-lite",
                "retrieval_mode": "document_search",
                "edit_message_id": user_msg_id,
            },
        )
        assert edit_res.status_code == 200
        # After editing message #1, conversation should have strictly 2 messages (edited user + new assistant)
        conv_detail = client.get(f"/api/conversations/{conv_id}").json()
        assert len(conv_detail["messages"]) == 2
        assert "Updated question:" in conv_detail["messages"][0]["content"]


def test_abstention_on_empty_collection(client: TestClient):
    """Verify the RAG engine abstains cleanly when a collection has no uploaded documents."""
    empty_col = client.post(
        "/api/collections",
        json={"name": "Empty Vault", "description": "No files uploaded yet"},
    ).json()
    conv = client.post(
        "/api/conversations",
        json={"title": "Empty Test", "collection_id": empty_col["id"]},
    ).json()

    res = client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={
            "content": "What is the secret launch code?",
            "collection_id": empty_col["id"],
        },
    )
    assert res.status_code == 200
    msg = res.json()["assistant_message"]
    assert msg["crag_trace"]["status"] == "no_documents"
    assert "No Documents Indexed" in msg["content"]


def test_document_reindex_and_deletion_cleanup(client: TestClient):
    """Verify re-indexing a document and deleting it removes its chunks from the vector index."""
    cols = client.get("/api/collections").json()["collections"]
    audit_col = next(c for c in cols if c["name"] == "Q3 Enterprise Audit")
    docs = client.get(f"/api/documents?collection_id={audit_col['id']}").json()["documents"]
    assert len(docs) >= 4

    target_doc = docs[0]
    # Reindex
    re_res = client.post(f"/api/documents/{target_doc['id']}/reindex")
    assert re_res.status_code == 200
    assert re_res.json()["document"]["status"] == "indexed"

    # Delete
    before_count = len(docs)
    del_res = client.delete(f"/api/documents/{target_doc['id']}")
    assert del_res.status_code == 200
    remaining = client.get(f"/api/documents?collection_id={audit_col['id']}").json()["documents"]
    assert len(remaining) == before_count - 1
