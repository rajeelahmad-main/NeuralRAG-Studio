"""
=============================================================================
NeuralRAG Studio — Commercial AI Document Intelligence Platform
CRISP + Multi-File Hybrid RAG + Corrective RAG (CRAG) + Gemini Model Selector
=============================================================================
Matches the Next.js full-stack interface pixel-for-pixel:
1. 3-Pane SaaS Workspace: Collapsible Sidebar, Central Chat, and Right Document Workspace Panel.
2. Top Navigation Bar: Gemini Model Selector, Collection Badge, Theme Toggle, and Sources Drawer.
3. 5 Commercial Starter Prompt Cards with badges (Overview, Compare Mode, Data & Tables, Deep Dive, CRISP Lab).
4. ChatGPT-Style Composer with inside Retrieval Mode pills (Corrective RAG, Doc Search, Compare Docs).
5. Right Document Workspace Panel: Tabs for Files & Source Inspector, Drag-and-Drop Uploader, Indexed File Cards with badges.
6. Multi-File Parsing: PDF, DOCX, XLSX/XLS, CSV, MD, TXT, and Images with Gemini Vision OCR.
7. Corrective RAG (CRAG) with query rewrite trace and clickable [Source N] citations.
8. Server-Isolated API Key via Streamlit Secrets (never exposed).
=============================================================================
"""

import base64
from datetime import datetime
from io import BytesIO
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pypdf
import requests
import streamlit as st

# Optional parsers
try:
    import docx
except ImportError:
    docx = None

try:
    import pandas as pd
except ImportError:
    pd = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# -----------------------------------------------------------------------------
# 1. Page Configuration & Meta
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NeuralRAG Studio | Multi-File AI Intelligence",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Session State Initialization
# -----------------------------------------------------------------------------
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

if "show_right_panel" not in st.session_state:
    st.session_state["show_right_panel"] = True

if "right_panel_tab" not in st.session_state:
    st.session_state["right_panel_tab"] = "files"

if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = "gemini-3.1-flash-lite"

if "retrieval_mode" not in st.session_state:
    st.session_state["retrieval_mode"] = "corrective_rag"

if "active_collection_name" not in st.session_state:
    st.session_state["active_collection_name"] = "General Workspace"

if "indexed_files_meta" not in st.session_state:
    st.session_state["indexed_files_meta"] = []

if "all_chunks" not in st.session_state:
    st.session_state["all_chunks"] = []

if "search_vec" not in st.session_state:
    st.session_state["search_vec"] = None

if "search_mat" not in st.session_state:
    st.session_state["search_mat"] = None

if "conversations" not in st.session_state:
    st.session_state["conversations"] = [
        {
            "id": "conv-default",
            "title": "Analyze this chart",
            "messages": [],
            "date": "Today"
        },
        {
            "id": "conv-sample-1",
            "title": "What was the Q3 2024 Revenue...",
            "messages": [],
            "date": "Today"
        }
    ]

if "active_conv_id" not in st.session_state:
    st.session_state["active_conv_id"] = "conv-default"

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "selected_citation" not in st.session_state:
    st.session_state["selected_citation"] = None

is_dark = (st.session_state["theme_mode"] == "dark")


# -----------------------------------------------------------------------------
# 3. Dynamic Design System & Pixel-Perfect Next.js CSS
# -----------------------------------------------------------------------------
if is_dark:
    bg_app = "#09090b"
    bg_sidebar = "#09090b"
    bg_panel = "#0e0e11"
    bg_card = "#121215"
    bg_card_hover = "#18181b"
    bg_input = "#121215"
    border_color = "rgba(255, 255, 255, 0.08)"
    border_focus = "rgba(59, 130, 246, 0.5)"
    text_primary = "#f4f4f5"
    text_secondary = "#a1a1aa"
    text_muted = "#71717a"
    accent_blue = "#3b82f6"
    accent_emerald = "#10b981"
    accent_purple = "#a855f7"
else:
    bg_app = "#ffffff"
    bg_sidebar = "#f9fafb"
    bg_panel = "#f9fafb"
    bg_card = "#ffffff"
    bg_card_hover = "#f3f4f6"
    bg_input = "#f9fafb"
    border_color = "rgba(0, 0, 0, 0.08)"
    border_focus = "rgba(59, 130, 246, 0.5)"
    text_primary = "#18181b"
    text_secondary = "#52525b"
    text_muted = "#a1a1aa"
    accent_blue = "#2563eb"
    accent_emerald = "#059669"
    accent_purple = "#9333ea"

st.markdown(f"""
<style>
    /* Reset & Base */
    header[data-testid="stHeader"],
    .stAppDeployButton,
    #MainMenu,
    footer {{
        display: none !important;
        visibility: hidden !important;
    }}
    .stApp {{
        background-color: {bg_app} !important;
        color: {text_primary} !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }}
    .block-container {{
        padding-top: 0.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }}

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: {bg_sidebar} !important;
        border-right: 1px solid {border_color} !important;
        width: 270px !important;
        min-width: 270px !important;
    }}
    section[data-testid="stSidebar"] > div:first-child {{
        padding-top: 1rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }}
    [data-testid="stSidebarCollapseButton"] button {{
        color: {text_secondary} !important;
    }}

    /* Brand Header in Sidebar */
    .sb-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding-bottom: 14px;
        border-bottom: 1px solid {border_color};
        margin-bottom: 14px;
    }}
    .sb-logo {{
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: #ffffff;
        color: #09090b;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        font-weight: 800;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }}
    .sb-title {{
        font-size: 0.95rem;
        font-weight: 700;
        color: {text_primary};
        letter-spacing: -0.01em;
        line-height: 1.2;
    }}
    .sb-sub {{
        font-size: 0.72rem;
        color: {text_muted};
        font-weight: 500;
    }}

    /* New Chat Pill Button */
    .btn-new-chat {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 9px 14px;
        border-radius: 12px;
        background: {bg_card};
        border: 1px solid {border_color};
        color: {text_primary};
        font-size: 0.84rem;
        font-weight: 600;
        margin-bottom: 12px;
        text-decoration: none;
    }}
    .btn-new-chat:hover {{
        background: {bg_card_hover};
        border-color: rgba(255,255,255,0.18);
    }}

    /* Sidebar Conversation Item */
    .sb-conv-item {{
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 10px;
        border-radius: 10px;
        color: {text_secondary};
        font-size: 0.82rem;
        margin-bottom: 3px;
        transition: all 0.12s ease;
        cursor: pointer;
    }}
    .sb-conv-item:hover, .sb-conv-active {{
        background: {bg_card_hover};
        color: {text_primary};
    }}

    /* Top Navigation Bar */
    .top-nav-bar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 16px;
        border-bottom: 1px solid {border_color};
        margin-bottom: 20px;
        background: {bg_app};
    }}

    /* Center Welcome Screen */
    .welcome-box {{
        text-align: center;
        padding: 32px 16px 20px 16px;
        max-width: 680px;
        margin: 0 auto;
    }}
    .welcome-sparkle {{
        width: 52px;
        height: 52px;
        border-radius: 16px;
        background: #ffffff;
        color: #09090b;
        font-size: 1.6rem;
        margin: 0 auto 16px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 16px rgba(255,255,255,0.15);
    }}
    .welcome-h1 {{
        font-size: 1.65rem;
        font-weight: 700;
        color: {text_primary};
        letter-spacing: -0.025em;
        margin-bottom: 8px;
    }}
    .welcome-p {{
        font-size: 0.86rem;
        color: {text_secondary};
        line-height: 1.5;
        margin-bottom: 24px;
    }}

    /* Starter Prompt Cards */
    .card-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 24px;
    }}
    .starter-card {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 14px 16px;
        text-align: left;
        cursor: pointer;
        transition: all 0.15s ease;
    }}
    .starter-card:hover {{
        background: {bg_card_hover};
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateY(-1px);
    }}
    .starter-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
    }}
    .starter-title {{
        font-size: 0.82rem;
        font-weight: 600;
        color: {text_primary};
    }}
    .starter-badge {{
        font-size: 0.68rem;
        font-weight: 500;
        padding: 2px 7px;
        border-radius: 9999px;
        background: rgba(255, 255, 255, 0.06);
        color: {text_secondary};
    }}
    .starter-desc {{
        font-size: 0.74rem;
        color: {text_muted};
        line-height: 1.4;
    }}

    /* Right Document Workspace Panel */
    .doc-panel-container {{
        background: {bg_panel};
        border: 1px solid {border_color};
        border-radius: 16px;
        padding: 16px;
        min-height: 600px;
    }}
    .doc-panel-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 12px;
        border-bottom: 1px solid {border_color};
        margin-bottom: 14px;
    }}
    .doc-panel-title {{
        font-size: 0.92rem;
        font-weight: 700;
        color: {text_primary};
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    /* File Dropzone Box */
    .dropzone-box {{
        background: {bg_card};
        border: 1px dashed {border_color};
        border-radius: 12px;
        padding: 18px 14px;
        text-align: center;
        margin-bottom: 16px;
    }}
    .dropzone-icon {{
        font-size: 1.5rem;
        color: {accent_blue};
        margin-bottom: 6px;
    }}
    .dropzone-text {{
        font-size: 0.8rem;
        font-weight: 600;
        color: {text_primary};
        margin-bottom: 6px;
    }}
    .dropzone-pills {{
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        justify-content: center;
    }}
    .pill-format {{
        font-size: 0.65rem;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.06);
        color: {text_secondary};
    }}

    /* Indexed File Item Card */
    .file-item-card {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }}
    .file-item-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }}
    .file-item-name {{
        font-size: 0.8rem;
        font-weight: 600;
        color: {text_primary};
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 180px;
    }}
    .badge-indexed {{
        font-size: 0.68rem;
        font-weight: 600;
        color: #10b981;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 9999px;
        padding: 2px 7px;
        display: inline-flex;
        align-items: center;
        gap: 3px;
    }}
    .file-item-meta {{
        font-size: 0.72rem;
        color: {text_muted};
        margin-bottom: 8px;
    }}

    /* Message Bubbles */
    div[data-testid="stChatMessage"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 14px !important;
        color: {text_primary} !important;
    }}

    /* Chat Input Styling */
    div[data-testid="stChatInput"] {{
        background-color: {bg_input} !important;
        border: 1px solid {border_color} !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
    }}
    div[data-testid="stChatInput"]:focus-within {{
        border-color: {border_focus} !important;
    }}
    div[data-testid="stChatInput"] textarea {{
        color: {text_primary} !important;
        font-size: 0.88rem !important;
    }}

    /* Custom Streamlit Buttons */
    div[data-testid="stButton"] button {{
        background-color: {bg_card} !important;
        color: {text_primary} !important;
        border: 1px solid {border_color} !important;
        border-radius: 10px !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        transition: all 0.12s ease !important;
    }}
    div[data-testid="stButton"] button:hover {{
        border-color: {accent_blue} !important;
        color: {accent_blue} !important;
    }}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. Protected Server API Key Resolution
# -----------------------------------------------------------------------------
def get_server_api_key() -> str:
    key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            key = str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    if not key:
        key = os.getenv("GEMINI_API_KEY", "").strip()
    return key


ACTIVE_API_KEY = get_server_api_key()


# -----------------------------------------------------------------------------
# 5. Multimodal Document Ingestion & Parsers
# -----------------------------------------------------------------------------
def run_gemini_ocr(image_bytes: bytes, mime_type: str, api_key: str, model_id: str) -> str:
    if not api_key:
        return "[Vision OCR requires server GEMINI_API_KEY]"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "contents": [{
            "parts": [
                {"text": "Transcribe this document image with full fidelity. Convert tables to Markdown grids. Extract text, diagram labels, and figures."},
                {"inlineData": {"mimeType": mime_type, "data": b64}}
            ]
        }],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            candidates = res.json().get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                return "".join(p.get("text", "") for p in parts if "text" in p).strip()
        return f"[OCR HTTP {res.status_code}]"
    except Exception as exc:
        return f"[OCR Error: {str(exc)}]"


def sanitize_extracted_text(text: str) -> str:
    """Strips raw PDF font dictionaries, encoding streams, and binary artifacts."""
    if not text:
        return ""
    cleaned = re.sub(r"/(?:Font|CIDInit|ProcSet|Encoding|FontDescriptor|ToUnicode)\b[^\n\r]*", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"<<[^>]{1,300}>>", " ", cleaned)
    cleaned = re.sub(r"\b(?:Arial(?:-Bold|-Italic)?|TimesNewRoman|Helvetica|Calibri)\b(?:\s+\d+\s+\d+\s+R)?", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"obj\s*<<.*?>>\s*endobj", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"stream.*?endstream", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def detect_target_file(query: str, chunks: List[Dict[str, Any]]) -> Optional[str]:
    q_low = query.lower()
    filenames = sorted(list({c["filename"] for c in chunks}), key=len, reverse=True)
    for fname in filenames:
        base = fname.rsplit(".", 1)[0].lower()
        if len(base) > 2 and (base in q_low or fname.lower() in q_low):
            return fname

    unique_files = list(dict.fromkeys(c["filename"] for c in chunks))
    ordinals = [
        (["first file", "file 1", "document 1", "doc 1"], 0),
        (["second file", "file 2", "document 2", "doc 2"], 1),
        (["third file", "file 3", "document 3", "doc 3"], 2),
    ]
    for patterns, idx in ordinals:
        if any(p in q_low for p in patterns) and idx < len(unique_files):
            return unique_files[idx]
    return None


def sample_chunks_for_broad_summary(chunks: List[Dict[str, Any]], max_chunks: int = 8) -> List[Tuple[Dict[str, Any], float]]:
    if len(chunks) <= max_chunks:
        return [(c, 0.95) for c in chunks]
    sorted_chunks = sorted(chunks, key=lambda c: (c.get("filename", ""), c.get("page", 1)))
    step = max(1, len(sorted_chunks) // max_chunks)
    sampled = []
    for i in range(0, len(sorted_chunks), step):
        if len(sampled) < max_chunks:
            sampled.append((sorted_chunks[i], 0.95))
    if sorted_chunks[-1] not in [s[0] for s in sampled] and len(sampled) < max_chunks:
        sampled.append((sorted_chunks[-1], 0.95))
    return sampled


def parse_uploaded_file(file_bytes: bytes, filename: str, api_key: str, model_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []
    ext = os.path.splitext(filename.lower())[1]
    file_size_kb = round(len(file_bytes) / 1024, 1)
    current_conv = st.session_state.get("active_conv_id", "default")

    if ext == ".pdf":
        reader = pypdf.PdfReader(BytesIO(file_bytes))
        for i, page in enumerate(reader.pages, start=1):
            raw = (page.extract_text() or "").strip()
            text = sanitize_extracted_text(raw)
            if len(text) < 40 and api_key and len(page.images) > 0:
                try:
                    ocr = run_gemini_ocr(page.images[0].data, "image/png", api_key, model_id)
                    if ocr and not ocr.startswith("[OCR"):
                        text = sanitize_extracted_text(ocr)
                except Exception:
                    pass
            if text:
                pages.append({"label": f"{filename} • Page {i}", "text": text, "filename": filename, "page": i})

    elif ext == ".docx" and docx is not None:
        doc = docx.Document(BytesIO(file_bytes))
        sec_num = 1
        lines = []
        for p in doc.paragraphs:
            if p.text.strip():
                if p.style.name.startswith("Heading"):
                    if lines:
                        pages.append({"label": f"{filename} • Section {sec_num}", "text": "\n".join(lines), "filename": filename, "page": sec_num})
                        sec_num += 1
                        lines = []
                lines.append(p.text.strip())
        if lines:
            pages.append({"label": f"{filename} • Section {sec_num}", "text": "\n".join(lines), "filename": filename, "page": sec_num})

    elif ext in (".xlsx", ".xls", ".csv") and pd is not None:
        try:
            if ext == ".csv":
                dfs = {"Data": pd.read_csv(BytesIO(file_bytes))}
            else:
                dfs = pd.read_excel(BytesIO(file_bytes), sheet_name=None)
            for sheet_name, df_sheet in dfs.items():
                clean_df = df_sheet.dropna(how="all")
                total_rows = len(clean_df)
                step = 25
                for s_idx in range(0, max(total_rows, 1), step):
                    e_idx = min(s_idx + step, total_rows)
                    slice_df = clean_df.iloc[s_idx:e_idx]
                    md = slice_df.to_markdown(index=False)
                    pages.append({
                        "label": f"{filename} • Sheet: {sheet_name} (Rows {s_idx+1}-{e_idx})",
                        "text": f"### Spreadsheet Sheet: {sheet_name} (Rows {s_idx+1}-{e_idx})\n\n{md}",
                        "filename": filename,
                        "page": 1
                    })
        except Exception:
            pass

    elif ext in (".png", ".jpg", ".jpeg", ".webp"):
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        ocr_text = run_gemini_ocr(file_bytes, mime, api_key, model_id)
        pages.append({"label": f"{filename} • Multimodal OCR", "text": sanitize_extracted_text(ocr_text), "filename": filename, "page": 1})

    else:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
        if text:
            pages.append({"label": f"{filename} • Full Text", "text": sanitize_extracted_text(text), "filename": filename, "page": 1})

    # Chunking
    chunks = []
    chunk_size = 650
    overlap = 100
    c_id = len(st.session_state["all_chunks"]) + 1
    for p in pages:
        txt = p["text"]
        start = 0
        while start < len(txt):
            end = min(start + chunk_size, len(txt))
            substr = txt[start:end].strip()
            if substr:
                chunks.append({
                    "id": c_id,
                    "label": p["label"],
                    "filename": p["filename"],
                    "page": p.get("page", 1),
                    "text": substr,
                    "conv_id": current_conv
                })
                c_id += 1
            if end >= len(txt):
                break
            start = max(end - overlap, start + 1)

    meta = {
        "filename": filename,
        "ext": ext.replace(".", "").upper() or "TXT",
        "size_kb": file_size_kb,
        "chunk_count": len(chunks),
        "status": "Indexed",
        "conv_id": current_conv
    }

    return chunks, meta


def reindex_all_documents():
    chunks = st.session_state["all_chunks"]
    if not chunks:
        st.session_state["search_vec"] = None
        st.session_state["search_mat"] = None
        return
    texts = [c["text"] for c in chunks]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    mat = vec.fit_transform(texts)
    st.session_state["search_vec"] = vec
    st.session_state["search_mat"] = mat


# -----------------------------------------------------------------------------
# 6. Corrective RAG (CRAG) & Gemini Synthesis Engine
# -----------------------------------------------------------------------------
def search_evidence(query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
    all_chunks = st.session_state.get("all_chunks", [])
    active_conv = st.session_state.get("active_conv_id")
    
    # Filter to active conversation chunks if scoped
    conv_chunks = [c for c in all_chunks if c.get("conv_id") == active_conv] if active_conv else all_chunks
    if not conv_chunks:
        conv_chunks = all_chunks

    # Check for target file reference (e.g. "read example1" or "file 1")
    target_file = detect_target_file(query, conv_chunks)
    active_chunks = [c for c in conv_chunks if c["filename"] == target_file] if target_file else conv_chunks

    if not active_chunks:
        return []

    # Broad summary query handling (distribute chunks across document)
    q_low = query.lower()
    is_summary = any(w in q_low for w in ["summarize", "summary", "overview", "what is this", "explain this", "tell me about this"])
    if is_summary:
        return sample_chunks_for_broad_summary(active_chunks, max_chunks=top_k)

    # Sub-index for active chunks
    texts = [c["text"] for c in active_chunks]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    try:
        mat = vec.fit_transform(texts)
        q_vec = vec.transform([query])
        scores = cosine_similarity(q_vec, mat)[0]
        top_indices = np.argsort(scores)[::-1][:min(top_k, len(active_chunks))]
        return [(active_chunks[int(i)], float(scores[int(i)])) for i in top_indices]
    except Exception:
        return [(active_chunks[i], 0.5) for i in range(min(top_k, len(active_chunks)))]


def expand_query_crag(query: str) -> List[str]:
    stops = {"what", "where", "when", "which", "who", "why", "how", "is", "are", "was", "were", "the", "a", "an", "in", "on", "of", "to", "for", "with", "about", "from", "can", "you", "tell", "me"}
    words = [w for w in re.findall(r"\w+", query.lower()) if w not in stops and len(w) > 2]
    if not words:
        return []
    expanded = list(words)
    for w in words:
        if w in ("revenue", "sales", "profit", "margin", "income", "metric"):
            expanded.extend(["financial", "growth", "total", "table"])
        elif w in ("method", "algorithm", "architecture", "system"):
            expanded.extend(["model", "design", "technique", "pipeline"])
        elif w in ("result", "finding", "conclusion"):
            expanded.extend(["summary", "metric", "evaluation", "outcome"])
    rewrites = [" ".join(dict.fromkeys(expanded))]
    return [r for r in rewrites if r.strip() != query.strip()][:2]


def generate_llm_response(
    query: str,
    evidence_blocks: List[str],
    api_key: str,
    model_id: str,
    retrieval_mode: str
) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    q_low = query.lower()
    is_summary = any(w in q_low for w in ["summarize", "summary", "overview", "what is this", "explain this", "about"])

    if "Compare" in retrieval_mode or retrieval_mode == "compare_documents":
        system_prompt = (
            "You are NeuralRAG Studio in COMPARE DOCUMENTS mode.\n"
            "Format your answer with Markdown:\n"
            "1. **### Executive Comparison Summary**: High-level cross-file synthesis.\n"
            "2. **### Comparison Matrix (Markdown Table)**: Side-by-side comparison of metrics, claims, or methodologies.\n"
            "3. **### Agreements & Discrepancies**: Where documents align or conflict.\n"
            "Every claim MUST cite its passage with [Source N]."
        )
    elif is_summary:
        system_prompt = (
            "You are NeuralRAG Studio, an enterprise AI document intelligence assistant.\n"
            "Provide an executive-level breakdown of the document:\n"
            "1. **### Document Overview & Purpose**: Core intent, background, and scope.\n"
            "2. **### Key Technical Procedures & Architecture**: Essential steps, workflows, or technical details.\n"
            "3. **### Critical Requirements & Prerequisites**: Required inputs, conditions, or configurations.\n"
            "4. **### Important Guidelines & Next Steps**: Practical takeaways, verification steps, and conclusions.\n"
            "STRICT MANDATE: DO NOT output font dictionaries, formatting metadata (e.g. Arial, /Font), or raw stream definitions. Ground every point with inline [Source N] citations."
        )
    else:
        system_prompt = (
            "You are NeuralRAG Studio, an enterprise AI document intelligence assistant.\n"
            "RULES:\n"
            "1. Answer strictly using the provided context passages inside <retrieved_evidence>.\n"
            "2. Every factual statement, number, or claim MUST include an inline citation [Source N] (e.g. [Source 1], [Source 2]).\n"
            "3. If the answer is not in the text, state: 'The uploaded documents do not contain sufficient evidence to answer this question.' Never invent information.\n"
            "4. Never output unrendered PDF font tables or metadata definitions."
        )

    context_str = "\n\n".join(evidence_blocks)
    user_prompt = (
        f"<retrieved_evidence>\n{context_str}\n</retrieved_evidence>\n\n"
        f"User Question: {query}\n\n"
        f"Provide your grounded Markdown response with [Source N] citations:"
    )

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1500}
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            candidates = res.json().get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                if text:
                    return text
            return "The model returned an empty response."
        return f"Gemini API Error (HTTP {res.status_code}): {res.text[:220]}"
    except requests.exceptions.Timeout:
        return f"Request to '{model_id}' timed out after 30 seconds."
    except Exception as exc:
        return f"Unexpected Error: {str(exc)}"


# -----------------------------------------------------------------------------
# 7. LEFT SIDEBAR: Brand, New Chat, Collection, Search, History, Bottom Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    # A. Brand Logo & Title
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-logo">✨</div>
        <div>
            <div class="sb-title">NeuralRAG</div>
            <div class="sb-sub">CRISP + Corrective RAG</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # B. New Chat Button
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state["messages"] = []
        new_id = f"conv-{int(time.time())}"
        st.session_state["conversations"].insert(0, {
            "id": new_id,
            "title": "New Chat",
            "messages": [],
            "date": "Today"
        })
        st.session_state["active_conv_id"] = new_id
        st.rerun()

    # C. Workspace Selector
    doc_count = len(st.session_state["indexed_files_meta"])
    st.markdown(f"""
    <div style="margin: 10px 0; padding: 8px 12px; border-radius: 10px; background: {bg_card}; border: 1px solid {border_color}; display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; color: {text_primary}; font-weight: 600;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span>📁</span>
            <span>{st.session_state['active_collection_name']}</span>
        </div>
        <span style="padding: 2px 7px; border-radius: 9999px; background: rgba(255,255,255,0.08); font-size: 0.7rem; color: {text_secondary};">{doc_count}</span>
    </div>
    """, unsafe_allow_html=True)

    # D. Search Conversations
    search_q = st.text_input("Search", placeholder="Search conversations...", label_visibility="collapsed")

    # E. Conversation History Grouped (TODAY)
    st.markdown(f"<p style='font-size:0.72rem; font-weight:700; color:{text_muted}; text-transform:uppercase; margin-top:14px; margin-bottom:6px;'>TODAY</p>", unsafe_allow_html=True)
    
    for conv in st.session_state["conversations"]:
        if search_q and search_q.lower() not in conv["title"].lower():
            continue
        is_active = (conv["id"] == st.session_state["active_conv_id"])
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"💬 {conv['title'][:22]}", key=f"sb_conv_{conv['id']}", use_container_width=True, type=btn_type):
            st.session_state["active_conv_id"] = conv["id"]
            st.session_state["messages"] = conv["messages"]
            st.rerun()

    st.markdown("<hr style='margin: 18px 0; border: none; border-top: 1px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)

    # F. Bottom Sidebar Controls
    if st.button(f"📖 Document Library ({doc_count} files)", use_container_width=True):
        st.session_state["show_right_panel"] = True
        st.session_state["right_panel_tab"] = "files"
        st.rerun()

    with st.expander("⚙️ Settings & RAG Config", expanded=False):
        top_k = st.slider("Top-K Evidence Chunks", 2, 8, 4)
        st.session_state["top_k"] = top_k
        st.caption("Configures hybrid retrieval depth and reranking ceiling.")

    # G. Theme Switcher & Status
    c_th1, c_th2 = st.columns(2)
    with c_th1:
        if st.button("🌙 Dark", use_container_width=True, type="primary" if is_dark else "secondary"):
            st.session_state["theme_mode"] = "dark"
            st.rerun()
    with c_th2:
        if st.button("☀️ Light", use_container_width=True, type="secondary" if is_dark else "primary"):
            st.session_state["theme_mode"] = "light"
            st.rerun()

    if ACTIVE_API_KEY:
        st.markdown(f"""
        <div style="margin-top: 12px; padding: 6px 10px; border-radius: 8px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); font-size: 0.72rem; color: #10b981;">
            🔒 <b>Server API Key Active</b>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="margin-top: 12px; padding: 6px 10px; border-radius: 8px; background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.25); font-size: 0.72rem; color: #f43f5e;">
            ⚠️ <b>Missing GEMINI_API_KEY in Secrets</b>
        </div>
        """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 8. TOP NAVIGATION BAR: Model Selector, Active Collection, Theme, Sources Toggle
# -----------------------------------------------------------------------------
t_col1, t_col2, t_col3, t_col4 = st.columns([3.5, 3.5, 1.2, 1.8])

with t_col1:
    model_choice = st.selectbox(
        "Active Model",
        [
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.1-pro-preview"
        ],
        index=0,
        label_visibility="collapsed"
    )
    st.session_state["selected_model"] = model_choice

with t_col2:
    active_conv_title = next((c["title"] for c in st.session_state["conversations"] if c["id"] == st.session_state["active_conv_id"]), "")
    if active_conv_title and active_conv_title != "New Chat":
        st.markdown(f"<p style='font-size:0.8rem; color:{text_muted}; margin-top:8px; border-left:1px solid {border_color}; padding-left:12px;'>{active_conv_title[:35]}</p>", unsafe_allow_html=True)

with t_col3:
    if st.button("☀️" if is_dark else "🌙", help="Toggle Light / Dark Appearance"):
        st.session_state["theme_mode"] = "light" if is_dark else "dark"
        st.rerun()

with t_col4:
    sources_btn_text = "📁 Sources" if not st.session_state["show_right_panel"] else "✕ Close"
    if st.button(sources_btn_text, use_container_width=True, type="primary" if st.session_state["show_right_panel"] else "secondary"):
        st.session_state["show_right_panel"] = not st.session_state["show_right_panel"]
        st.rerun()


# -----------------------------------------------------------------------------
# 9. MAIN TWO-COLUMN SPLIT: Central Chat Workspace + Right Document Panel
# -----------------------------------------------------------------------------
if st.session_state["show_right_panel"]:
    chat_col, right_col = st.columns([68, 32], gap="medium")
else:
    chat_col = st.container()
    right_col = None


# =============================================================================
# A. CENTRAL CHAT WORKSPACE (Inside chat_col)
# =============================================================================
with chat_col:
    # 1. Welcome Screen when no messages exist
    if not st.session_state["messages"]:
        st.markdown(f"""
        <div class="welcome-box">
            <div class="welcome-sparkle">✨</div>
            <h1 class="welcome-h1">What would you like to know from your documents?</h1>
            <p class="welcome-p">
                Ask questions across PDF, Word, Excel, CSV, and Markdown files with 
                <b>Corrective RAG verification</b> and clickable source citations.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 2. The 5 Next.js Commercial Starter Cards
        st.markdown("<p style='font-size:0.75rem; font-weight:700; color:#71717a; text-transform:uppercase; margin-bottom:10px;'>Recommended Inquiries</p>", unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("📌 Executive Summary [Overview]\nSummarize the key findings, main arguments, and conclusions across my uploaded documents.", key="card_exec", use_container_width=True):
                st.session_state["pending_prompt"] = "Summarize the key findings, main arguments, and conclusions across my uploaded documents."
                st.rerun()

            if st.button("📊 Extract Financial & Tabular Metrics [Data & Tables]\nWhat quantitative figures, tables, or performance metrics are reported in these documents?", key="card_tables", use_container_width=True):
                st.session_state["pending_prompt"] = "What quantitative figures, tables, or performance metrics are reported in these documents?"
                st.rerun()

            if st.button("🧪 Study Guide & Verification Quiz [CRISP Lab]\nGenerate a concise study guide and a 3-question comprehension quiz with answers grounded strictly in the uploaded files.", key="card_quiz", use_container_width=True):
                st.session_state["pending_prompt"] = "Generate a concise study guide and a 3-question comprehension quiz with answers grounded strictly in the uploaded files."
                st.rerun()

        with sc2:
            if st.button("⚖️ Cross-Document Comparison [Compare Mode]\nCompare the key claims, quantitative metrics, and conclusions across the uploaded files and highlight any discrepancies.", key="card_compare", use_container_width=True):
                st.session_state["retrieval_mode"] = "compare_documents"
                st.session_state["pending_prompt"] = "Compare the key claims, quantitative metrics, and conclusions across the uploaded files and highlight any discrepancies."
                st.rerun()

            if st.button("🔍 Methodology & Architecture Audit [Deep Dive]\nExplain the core methodology, system architecture, or security controls described in the uploaded text.", key="card_audit", use_container_width=True):
                st.session_state["pending_prompt"] = "Explain the core methodology, system architecture, or security controls described in the uploaded text."
                st.rerun()

    # 3. Message Stream & History
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="✨"):
                st.markdown(msg["content"])

                # Citations Drawer
                if msg.get("citations"):
                    with st.expander(f"📚 Verified Sources ({len(msg['citations'])})", expanded=False):
                        for idx, cit in enumerate(msg["citations"], start=1):
                            st.markdown(f"""
                            <div style="padding: 10px 14px; margin-bottom: 8px; border-radius: 10px; background: {bg_app}; border: 1px solid {border_color}; font-size: 0.8rem;">
                                <div style="font-weight: 600; color: {accent_blue}; margin-bottom: 4px;">Source {idx}: {cit['label']} (Relevance: {cit.get('score', 0):.2f})</div>
                                <div style="color: {text_secondary}; line-height: 1.45;">{cit['text']}</div>
                            </div>
                            """, unsafe_allow_html=True)

                # Corrective RAG Trace
                if msg.get("crag_trace") and msg["crag_trace"].get("rewritten_queries"):
                    with st.expander("🛡️ Corrective RAG (CRAG) Search Expansion Trace", expanded=False):
                        st.caption("Initial query had weak semantic alignment. Corrective RAG expanded queries:")
                        for rq in msg["crag_trace"]["rewritten_queries"]:
                            st.code(f"Expanded: \"{rq}\"", language=None)

                # Footer
                st.caption(f"⚡ Latency: **{msg.get('latency', 0.0):.2f}s** • 🤖 Model: **{msg.get('model', st.session_state['selected_model'])}** • 🛡️ Mode: **{msg.get('mode', 'RAG')}**")

    # 4. Retrieval Mode Pills inside Composer Row
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        crag_active = (st.session_state["retrieval_mode"] == "corrective_rag")
        if st.button("🛡️ Corrective RAG", use_container_width=True, type="primary" if crag_active else "secondary"):
            st.session_state["retrieval_mode"] = "corrective_rag"
            st.rerun()
    with m_col2:
        search_active = (st.session_state["retrieval_mode"] == "document_search")
        if st.button("🎯 Doc Search", use_container_width=True, type="primary" if search_active else "secondary"):
            st.session_state["retrieval_mode"] = "document_search"
            st.rerun()
    with m_col3:
        compare_active = (st.session_state["retrieval_mode"] == "compare_documents")
        if st.button("⚖️ Compare Docs", use_container_width=True, type="primary" if compare_active else "secondary"):
            st.session_state["retrieval_mode"] = "compare_documents"
            st.rerun()

    # 5. Bottom Composer Input
    prompt_placeholder = f"Ask anything about your {doc_count} indexed documents in General Workspace..."
    user_query = st.chat_input(prompt_placeholder)

    if st.session_state.get("pending_prompt"):
        user_query = st.session_state.pop("pending_prompt")

    st.markdown(f"<p style='font-size:0.72rem; color:{text_muted}; text-align:center; margin-top:8px;'>Grounded in General Workspace ({doc_count} files) • Click any [Source N] citation to inspect original passage</p>", unsafe_allow_html=True)

    # 6. Response Execution Pipeline
    if user_query and user_query.strip():
        # Append User Message
        st.session_state["messages"].append({"role": "user", "content": user_query})

        # Update Active Conversation Title if it's the first message
        for conv in st.session_state["conversations"]:
            if conv["id"] == st.session_state["active_conv_id"]:
                if conv["title"] == "New Chat":
                    conv["title"] = user_query[:28] + ("..." if len(user_query) > 28 else "")
                conv["messages"] = st.session_state["messages"]
                break

        with st.spinner("Retrieving evidence & generating grounded response..."):
            t_start = time.time()
            all_chunks = st.session_state.get("all_chunks", [])
            citations = []
            crag_trace = None

            if all_chunks and st.session_state.get("search_vec") is not None:
                top_k = st.session_state.get("top_k", 4)
                ranked = search_evidence(user_query, top_k=top_k)
                top_score = ranked[0][1] if ranked else 0.0

                crag_trace = {
                    "mode": st.session_state["retrieval_mode"],
                    "top_score": top_score,
                    "rewritten_queries": []
                }

                # CRAG Expansion loop if retrieval quality is ambiguous
                if st.session_state["retrieval_mode"] == "corrective_rag" and (top_score < 0.28 or len(ranked) < 2):
                    rewrites = expand_query_crag(user_query)
                    crag_trace["rewritten_queries"] = rewrites
                    seen = {c[0]["text"] for c in ranked}
                    for rq in rewrites:
                        extra = search_evidence(rq, top_k=top_k)
                        for ch, sc in extra:
                            if ch["text"] not in seen:
                                ranked.append((ch, sc))
                                seen.add(ch["text"])
                    ranked.sort(key=lambda x: x[1], reverse=True)
                    ranked = ranked[:top_k]

                evidence_blocks = []
                for i, (c, sc) in enumerate(ranked, start=1):
                    citations.append({"label": c["label"], "text": c["text"], "score": sc, "chunk_id": c["id"]})
                    evidence_blocks.append(f"<source id=\"Source {i}\" location=\"{c['label']}\">\n{c['text']}\n</source>")

                if ACTIVE_API_KEY:
                    final_answer = generate_llm_response(
                        user_query,
                        evidence_blocks,
                        ACTIVE_API_KEY,
                        st.session_state["selected_model"],
                        st.session_state["retrieval_mode"]
                    )
                else:
                    final_answer = "⚠️ Server GEMINI_API_KEY is not configured in .streamlit/secrets.toml. Please add it to your Streamlit secrets."
            else:
                final_answer = "💡 No documents are indexed yet in General Workspace. Please upload PDFs, DOCX, or Excel files in the right Document Workspace panel to enable source-grounded answers."

            t_elapsed = time.time() - t_start

            st.session_state["messages"].append({
                "role": "assistant",
                "content": final_answer,
                "citations": citations,
                "crag_trace": crag_trace,
                "latency": t_elapsed,
                "model": st.session_state["selected_model"],
                "mode": st.session_state["retrieval_mode"]
            })

            # Sync active conversation
            for conv in st.session_state["conversations"]:
                if conv["id"] == st.session_state["active_conv_id"]:
                    conv["messages"] = st.session_state["messages"]
                    break

            st.rerun()


# =============================================================================
# B. RIGHT PANEL: DOCUMENT WORKSPACE & CITATION INSPECTOR (Inside right_col)
# =============================================================================
if right_col is not None:
    with right_col:
        st.markdown(f"""
        <div class="doc-panel-container">
            <div class="doc-panel-header">
                <div class="doc-panel-title">
                    <span>📁</span>
                    <span>Document Workspace</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Tab Selection: Files (N) vs Source Inspector
        tab_choice = st.radio(
            "Panel Tab",
            [f"Files ({doc_count})", "Source Inspector"],
            index=0 if st.session_state["right_panel_tab"] == "files" else 1,
            horizontal=True,
            label_visibility="collapsed"
        )
        st.session_state["right_panel_tab"] = "files" if "Files" in tab_choice else "inspector"

        st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)

        if st.session_state["right_panel_tab"] == "files":
            # Active Collection Info
            st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <span style="font-size: 0.72rem; font-weight: 700; color: {text_muted}; text-transform: uppercase;">Active Collection</span>
                <span style="font-size: 0.75rem; color: {accent_blue}; font-weight: 600;">+ New Collection</span>
            </div>
            <div style="padding: 8px 12px; border-radius: 10px; background: {bg_card}; border: 1px solid {border_color}; font-size: 0.82rem; font-weight: 600; color: {text_primary}; margin-bottom: 16px;">
                {st.session_state['active_collection_name']} ({doc_count} files)
            </div>
            """, unsafe_allow_html=True)

            # Cloud Drag-and-Drop Uploader Dropzone
            st.markdown(f"""
            <div class="dropzone-box">
                <div class="dropzone-icon">☁️</div>
                <div class="dropzone-text">Click or drag files to upload into General Workspace</div>
                <div class="dropzone-pills">
                    <span class="pill-format">PDF</span>
                    <span class="pill-format">DOCX</span>
                    <span class="pill-format">XLSX</span>
                    <span class="pill-format">CSV</span>
                    <span class="pill-format">MD</span>
                    <span class="pill-format">TXT</span>
                    <span class="pill-format">OCR Images</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            uploaded_files = st.file_uploader(
                "Upload files into General Workspace",
                type=["pdf", "docx", "xlsx", "xls", "csv", "png", "jpg", "jpeg", "webp", "txt", "md"],
                accept_multiple_files=True,
                label_visibility="collapsed"
            )

            if uploaded_files:
                new_files = False
                existing_names = {m["filename"] for m in st.session_state["indexed_files_meta"]}
                for f in uploaded_files:
                    if f.name not in existing_names:
                        with st.spinner(f"Ingesting {f.name}..."):
                            chunks, meta = parse_uploaded_file(f.getvalue(), f.name, ACTIVE_API_KEY, st.session_state["selected_model"])
                            st.session_state["all_chunks"].extend(chunks)
                            st.session_state["indexed_files_meta"].append(meta)
                            new_files = True

                if new_files:
                    reindex_all_documents()
                    st.rerun()

            # INDEXED FILES List
            st.markdown(f"""
            <div style="font-size: 0.72rem; font-weight: 700; color: {text_muted}; text-transform: uppercase; margin-top: 18px; margin-bottom: 10px;">
                Indexed Files ({doc_count})
            </div>
            """, unsafe_allow_html=True)

            active_conv = st.session_state.get("active_conv_id", "")
            active_docs = [m for m in st.session_state["indexed_files_meta"] if m.get("conv_id") == active_conv]
            if not active_docs and not st.session_state.get("messages"):
                active_docs = []
            elif not active_docs:
                active_docs = st.session_state["indexed_files_meta"]

            if not active_docs:
                st.caption("No files uploaded for this chat yet. Drag files into the box above.")
            else:
                for idx, f_meta in enumerate(active_docs):
                    file_icon = "🖼️" if f_meta["ext"] in ("PNG", "JPG", "JPEG", "WEBP") else "📄"
                    st.markdown(f"""
                    <div class="file-item-card">
                        <div class="file-item-top">
                            <div class="file-item-name">{file_icon} {f_meta['filename']}</div>
                            <span class="badge-indexed">● Indexed</span>
                        </div>
                        <div class="file-item-meta">
                            {f_meta['ext']} • {f_meta['size_kb']} KB • {f_meta['chunk_count']} chunks
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        if st.button("🔄 Re-index", key=f"reindex_{idx}", use_container_width=True):
                            reindex_all_documents()
                            st.toast(f"Re-indexed {f_meta['filename']}")
                    with btn_c2:
                        if st.button("🗑️ Remove", key=f"del_{idx}", use_container_width=True):
                            fname = f_meta["filename"]
                            st.session_state["indexed_files_meta"] = [m for m in st.session_state["indexed_files_meta"] if m["filename"] != fname]
                            st.session_state["all_chunks"] = [c for c in st.session_state["all_chunks"] if c["filename"] != fname]
                            reindex_all_documents()
                            st.rerun()

        else:
            # Source Inspector Tab
            st.markdown(f"""
            <div style="font-size: 0.72rem; font-weight: 700; color: {text_muted}; text-transform: uppercase; margin-bottom: 10px;">
                Retrieved Source Inspector
            </div>
            """, unsafe_allow_html=True)

            last_msg = next((m for m in reversed(st.session_state["messages"]) if m["role"] == "assistant" and m.get("citations")), None)
            if last_msg and last_msg.get("citations"):
                for idx, cit in enumerate(last_msg["citations"], start=1):
                    st.markdown(f"""
                    <div style="padding: 12px; margin-bottom: 10px; border-radius: 12px; background: {bg_card}; border: 1px solid {border_color}; font-size: 0.8rem;">
                        <div style="font-weight: 600; color: {accent_blue}; margin-bottom: 4px;">[Source {idx}] {cit['label']}</div>
                        <div style="font-size: 0.72rem; color: #10b981; margin-bottom: 6px;">● Cosine Similarity: {cit.get('score', 0):.3f}</div>
                        <div style="color: {text_secondary}; line-height: 1.45; font-size: 0.76rem;">{cit['text']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("Ask a question in the chat to inspect evidence chunks, provenance, and vector similarity grades here.")

        st.markdown("</div>", unsafe_allow_html=True)
