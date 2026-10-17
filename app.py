"""
=============================================================================
NeuralRAG Studio — Commercial AI Document Intelligence Platform
CRISP + Multi-File Hybrid RAG + Corrective RAG (CRAG) + Gemini Model Selector
=============================================================================
A modern ChatGPT-inspired full-stack document workspace in Streamlit:
1. ChatGPT-Style Layout: Clean sidebar, centered landing, and bottom composer.
2. Server-Side Protected API Key: Exclusively uses server key; never leaks.
3. Multi-File Ingestion: PDF (Digital + OCR), Word (.docx), Excel/CSV, Markdown, Images.
4. Gemini Model Selector: gemini-3.1-flash-lite, gemini-3.5-flash, gemini-3.5-flash-lite, gemini-3.1-pro-preview.
5. 3 Retrieval Modes: Corrective RAG (CRAG), Document Search, Compare Documents.
6. Clickable [Source N] Citations with document, page, heading, and row provenance.
7. Pure Black Dark Theme & Clean Light Theme with 1-click toggle buttons.
=============================================================================
"""

import base64
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

# Optional third-party parsers
try:
    import docx
except ImportError:
    docx = None

try:
    import pandas as pd
except ImportError:
    pd = None


# -----------------------------------------------------------------------------
# 1. Page Configuration & Title
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NeuralRAG — Commercial AI Document Intelligence",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Dual-Theme Styling System (Pure Dark #09090b & Clean Light #ffffff)
# -----------------------------------------------------------------------------
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

is_dark = (st.session_state["theme_mode"] == "dark")

if is_dark:
    t_bg_app = "#09090b"
    t_bg_sidebar = "#0f0f12"
    t_bg_card = "#18181b"
    t_border = "#27272a"
    t_text_primary = "#f4f4f5"
    t_text_secondary = "#a1a1aa"
    t_accent = "#3b82f6"
    t_accent_glow = "rgba(59, 130, 246, 0.15)"
    t_user_bg = "#27272a"
    t_asst_bg = "#121215"
    t_input_bg = "#18181b"
    t_btn_bg = "#18181b"
else:
    t_bg_app = "#ffffff"
    t_bg_sidebar = "#f8fafc"
    t_bg_card = "#ffffff"
    t_border = "#e2e8f0"
    t_text_primary = "#0f172a"
    t_text_secondary = "#64748b"
    t_accent = "#2563eb"
    t_accent_glow = "rgba(37, 99, 235, 0.10)"
    t_user_bg = "#f1f5f9"
    t_asst_bg = "#ffffff"
    t_input_bg = "#ffffff"
    t_btn_bg = "#ffffff"

st.markdown(f"""
<style>
    /* Complete Removal of Deploy Button, Header Chrome & Status */
    .stAppDeployButton,
    [data-testid="stAppDeployButton"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"],
    #MainMenu,
    header[data-testid="stHeader"],
    .stAppHeader {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        width: 0px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 4rem !important;
        max-width: 900px !important;
    }}

    /* Canvas & Global Typography */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMainBlockContainer"] {{
        background-color: {t_bg_app} !important;
        color: {t_text_primary} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}

    /* Sidebar Styling */
    section[data-testid="stSidebar"],
    [data-testid="stSidebarHeader"],
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"],
    [data-testid="stSidebarNav"] {{
        background-color: {t_bg_sidebar} !important;
        border-right: 1px solid {t_border} !important;
        color: {t_text_primary} !important;
    }}
    [data-testid="stSidebarHeader"] {{
        background-color: {t_bg_sidebar} !important;
        border-bottom: 1px solid {t_border} !important;
        padding: 0.5rem 1rem !important;
    }}
    [data-testid="stSidebarCollapseButton"] button {{
        color: {t_text_primary} !important;
    }}

    /* File Uploader Box */
    [data-testid="stFileUploader"],
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploadDropzone"],
    [data-testid="stFileUploaderDropzone"],
    section[data-testid="stFileUploadDropzone"],
    div[data-testid="stFileUploaderDropzone"] {{
        background-color: {t_input_bg} !important;
        border: 1px dashed {t_border} !important;
        border-radius: 12px !important;
        color: {t_text_primary} !important;
    }}
    [data-testid="stFileUploader"] section:hover,
    [data-testid="stFileUploadDropzone"]:hover {{
        border-color: {t_accent} !important;
        background-color: {t_accent_glow} !important;
    }}
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploadDropzone"] small,
    [data-testid="stFileUploadDropzone"] span {{
        color: {t_text_secondary} !important;
    }}

    /* Sticky Bottom Composer Area */
    div[data-testid="stBottom"],
    div[data-testid="stBottom"] > div,
    footer {{
        background-color: {t_bg_app} !important;
        border-top: none !important;
    }}
    div[data-testid="stChatInput"] {{
        background-color: {t_input_bg} !important;
        border: 1px solid {t_border} !important;
        border-radius: 24px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        padding: 2px !important;
    }}
    div[data-testid="stChatInput"] > div {{
        background-color: {t_input_bg} !important;
        border: none !important;
        border-radius: 22px !important;
    }}
    div[data-testid="stChatInput"] textarea {{
        background-color: transparent !important;
        color: {t_text_primary} !important;
        font-size: 0.95rem !important;
    }}
    div[data-testid="stChatInput"] button {{
        background-color: {t_accent} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 50% !important;
    }}

    /* Clean Buttons */
    div[data-testid="stButton"] button {{
        background-color: {t_btn_bg} !important;
        color: {t_text_primary} !important;
        border: 1px solid {t_border} !important;
        border-radius: 10px !important;
        padding: 8px 14px !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }}
    div[data-testid="stButton"] button:hover {{
        border-color: {t_accent} !important;
        color: {t_accent} !important;
    }}

    /* Chat Messages */
    div[data-testid="stChatMessage"] {{
        background-color: {t_asst_bg} !important;
        border: 1px solid {t_border} !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        color: {t_text_primary} !important;
    }}

    /* Brand Header */
    .brand-header {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding-bottom: 12px;
        border-bottom: 1px solid {t_border};
        margin-bottom: 12px;
    }}
    .brand-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {t_text_primary};
        letter-spacing: -0.02em;
    }}
    .brand-sub {{
        font-size: 0.74rem;
        color: {t_text_secondary};
    }}

    /* Welcome Banner */
    .welcome-container {{
        text-align: center;
        padding: 40px 10px 24px 10px;
    }}
    .welcome-logo {{
        width: 52px;
        height: 52px;
        line-height: 52px;
        border-radius: 16px;
        background: {t_accent};
        color: #ffffff;
        font-size: 1.6rem;
        margin: 0 auto 16px auto;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .welcome-title {{
        font-size: 1.7rem;
        font-weight: 700;
        color: {t_text_primary};
        margin-bottom: 6px;
        letter-spacing: -0.01em;
    }}
    .welcome-sub {{
        font-size: 0.95rem;
        color: {t_text_secondary};
        max-width: 580px;
        margin: 0 auto;
        line-height: 1.5;
    }}

    /* Pill Badges */
    .pill-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: {t_bg_card};
        border: 1px solid {t_border};
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.78rem;
        font-weight: 600;
        color: {t_text_secondary};
    }}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 3. Server API Key Management & Diagnostics
# -----------------------------------------------------------------------------
def get_primary_api_key() -> Tuple[str, str]:
    key = ""
    source = "Not Configured"
    try:
        if "GEMINI_API_KEY" in st.secrets:
            key = str(st.secrets["GEMINI_API_KEY"]).strip()
            source = "Streamlit Secrets (.streamlit/secrets.toml)"
    except Exception:
        pass

    if not key:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if key:
            source = "Environment Variable (GEMINI_API_KEY)"

    return key, source


def check_api_health(api_key: str, model_id: str = "gemini-3.1-flash-lite") -> Dict[str, Any]:
    if not api_key:
        return {"status": "error", "message": "Server GEMINI_API_KEY is not configured.", "latency_ms": 0}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    payload = {
        "contents": [{"parts": [{"text": "Reply with OK."}]}],
        "generationConfig": {"maxOutputTokens": 5, "temperature": 0.0}
    }
    t0 = time.time()
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        latency = int((time.time() - t0) * 1000)
        if res.status_code == 200:
            return {"status": "success", "latency_ms": latency, "model": model_id}
        return {"status": "error", "code": res.status_code, "message": res.text, "latency_ms": latency}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "latency_ms": int((time.time() - t0) * 1000)}


# -----------------------------------------------------------------------------
# 4. Multimodal Parsers (PDF + Vision OCR, Word, Excel, CSV, Images, Text)
# -----------------------------------------------------------------------------
def run_gemini_vision_ocr(image_bytes: bytes, mime_type: str, api_key: str, model: str) -> str:
    if not api_key:
        return "[Vision OCR requires server GEMINI_API_KEY]"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
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


def parse_single_file(file_bytes: bytes, filename: str, api_key: str, model: str) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []
    ext = os.path.splitext(filename.lower())[1]

    if ext == ".pdf":
        reader = pypdf.PdfReader(BytesIO(file_bytes))
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if len(text) < 40 and api_key and len(page.images) > 0:
                try:
                    first_img = page.images[0]
                    ocr = run_gemini_vision_ocr(first_img.data, "image/png", api_key, model)
                    if ocr and not ocr.startswith("[OCR"):
                        text = f"{text}\n\n[Scanned Page OCR]:\n{ocr}".strip()
                except Exception:
                    pass
            if text:
                pages.append({"label": f"{filename} • Page {i}", "text": text, "filename": filename, "page": i})

    elif ext == ".docx" and docx is not None:
        doc = docx.Document(BytesIO(file_bytes))
        sec_num = 1
        current_lines = []
        for p in doc.paragraphs:
            if p.text.strip():
                if p.style.name.startswith("Heading"):
                    if current_lines:
                        pages.append({"label": f"{filename} • Section {sec_num}", "text": "\n".join(current_lines), "filename": filename, "page": sec_num})
                        sec_num += 1
                        current_lines = []
                current_lines.append(p.text.strip())
        if current_lines:
            pages.append({"label": f"{filename} • Section {sec_num}", "text": "\n".join(current_lines), "filename": filename, "page": sec_num})

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
        ocr_text = run_gemini_vision_ocr(file_bytes, mime, api_key, model)
        pages.append({"label": f"{filename} • Multimodal OCR", "text": ocr_text, "filename": filename, "page": 1})

    else:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
        if text:
            pages.append({"label": f"{filename} • Full Text", "text": text, "filename": filename, "page": 1})

    return pages


def build_chunks(pages: List[Dict[str, Any]], chunk_size: int = 650, overlap: int = 100) -> List[Dict[str, Any]]:
    chunks = []
    c_id = 1
    for p in pages:
        txt = p["text"]
        start = 0
        while start < len(txt):
            end = min(start + chunk_size, len(txt))
            chunk_str = txt[start:end].strip()
            if chunk_str:
                chunks.append({
                    "id": c_id,
                    "label": p["label"],
                    "filename": p["filename"],
                    "page": p.get("page", 1),
                    "text": chunk_str
                })
                c_id += 1
            if end >= len(txt):
                break
            start = max(end - overlap, start + 1)
    return chunks


# -----------------------------------------------------------------------------
# 5. Hybrid Retrieval & Corrective RAG (CRAG) Engine
# -----------------------------------------------------------------------------
def build_search_index(chunks: List[Dict[str, Any]]):
    from sklearn.feature_extraction.text import TfidfVectorizer
    texts = [c["text"] for c in chunks]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    matrix = vec.fit_transform(texts)
    return vec, matrix


def search_chunks(query: str, chunks: List[Dict[str, Any]], vec, matrix, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
    from sklearn.metrics.pairwise import cosine_similarity
    q_vec = vec.transform([query])
    scores = cosine_similarity(q_vec, matrix)[0]
    top_indices = np.argsort(scores)[::-1][:min(top_k, len(chunks))]
    return [(chunks[int(i)], float(scores[int(i)])) for i in top_indices]


def expand_query_for_crag(query: str) -> List[str]:
    stops = {"what", "where", "when", "which", "who", "why", "how", "is", "are", "was", "were", "the", "a", "an", "in", "on", "of", "to", "for", "with", "about", "from", "can", "you", "tell", "me"}
    words = [w for w in re.findall(r"\w+", query.lower()) if w not in stops and len(w) > 2]
    if not words:
        return []
    rewrites = [" ".join(words)]
    expanded = list(words)
    for w in words:
        if w in ("revenue", "sales", "profit", "margin", "income"):
            expanded.extend(["financial", "growth", "total", "table"])
        elif w in ("method", "algorithm", "architecture", "system"):
            expanded.extend(["model", "design", "technique", "pipeline"])
        elif w in ("result", "finding", "conclusion"):
            expanded.extend(["summary", "metric", "evaluation", "outcome"])
    rewrites.append(" ".join(dict.fromkeys(expanded)))
    return [r for r in rewrites if r.strip() != query.strip()][:2]


def execute_llm_generation(
    query: str,
    evidence_blocks: List[str],
    api_key: str,
    model_id: str,
    retrieval_mode: str
) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    if "Compare" in retrieval_mode:
        system_prompt = (
            "You are NeuralRAG, an enterprise document intelligence assistant in COMPARE DOCUMENTS mode.\n"
            "Format your answer with Markdown:\n"
            "1. **### Executive Comparison Summary**: High-level cross-file synthesis.\n"
            "2. **### Comparison Matrix (Markdown Table)**: Side-by-side comparison of metrics, claims, or methodologies.\n"
            "3. **### Agreements & Discrepancies**: Where documents align or conflict.\n"
            "Every claim MUST cite its passage with [Source N | File]."
        )
    else:
        system_prompt = (
            "You are NeuralRAG, an enterprise AI document intelligence assistant.\n"
            "RULES:\n"
            "1. Answer strictly using the provided context passages inside <retrieved_evidence>.\n"
            "2. Every claim, number, or quote MUST include an inline citation [Source N] (e.g., [Source 1], [Source 2]).\n"
            "3. If the answer is not supported by the passages, state: 'The uploaded documents do not contain sufficient evidence to answer this question.' Never speculate."
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
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1400}
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
        else:
            return f"Gemini API Error (HTTP {res.status_code}): {res.text[:200]}"
    except requests.exceptions.Timeout:
        return f"Request to '{model_id}' timed out after 30 seconds."
    except Exception as exc:
        return f"Unexpected Error: {str(exc)}"


# -----------------------------------------------------------------------------
# 6. Sidebar: Logo, New Chat, Multi-File Uploader, Model, Theme
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="brand-header">
        <div style="width: 32px; height: 32px; border-radius: 8px; background: #3b82f6; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; font-weight: 800;">N</div>
        <div>
            <div class="brand-title">NeuralRAG</div>
            <div class="brand-sub">AI Document Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state["messages"] = []
        st.rerun()

    st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    # Multi-File Knowledge Base
    st.markdown("<p style='font-size:0.82rem; font-weight:700; margin-bottom:4px;'>📁 Document Library</p>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Upload files",
        type=["pdf", "docx", "xlsx", "xls", "csv", "png", "jpg", "jpeg", "webp", "txt", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Upload multiple documents for unified cross-file intelligence."
    )

    # Retrieval Strategy
    st.markdown("<p style='font-size:0.82rem; font-weight:700; margin-top:10px; margin-bottom:4px;'>🛡️ Retrieval Mode</p>", unsafe_allow_html=True)
    retrieval_mode = st.radio(
        "Retrieval Mode",
        [
            "🛡️ Corrective RAG (CRAG)",
            "🎯 Document Search",
            "⚖️ Compare Documents"
        ],
        index=0,
        label_visibility="collapsed"
    )

    # Gemini Model Selector
    st.markdown("<p style='font-size:0.82rem; font-weight:700; margin-top:10px; margin-bottom:4px;'>🤖 Gemini Model</p>", unsafe_allow_html=True)
    gemini_model = st.selectbox(
        "Gemini Model",
        [
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.1-pro-preview",
            "gemini-flash-lite-latest"
        ],
        index=0,
        label_visibility="collapsed"
    )

    # Top-K Evidence Chunks
    top_k = st.slider("Evidence Chunks (Top-K)", min_value=2, max_value=8, value=4)

    st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    # Theme Toggle Buttons (🌙 Dark / ☀️ Light)
    st.markdown("<p style='font-size:0.82rem; font-weight:700; margin-bottom:6px;'>🎨 Appearance Theme</p>", unsafe_allow_html=True)
    tc1, tc2 = st.columns(2)
    with tc1:
        if st.button("🌙 Dark", use_container_width=True, type="primary" if is_dark else "secondary"):
            st.session_state["theme_mode"] = "dark"
            st.rerun()
    with tc2:
        if st.button("☀️ Light", use_container_width=True, type="secondary" if is_dark else "primary"):
            st.session_state["theme_mode"] = "light"
            st.rerun()

    # Protected Server API Key Badge
    active_key, key_source = get_primary_api_key()
    if active_key:
        st.markdown(f"""
        <div style="margin-top: 14px; padding: 8px 12px; border-radius: 8px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); font-size: 0.74rem; color: #10b981;">
            🔒 <b>Server API Key: Protected & Active</b><br>
            <span style="color: {t_text_secondary};">Credentials isolated on server</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ GEMINI_API_KEY missing in .streamlit/secrets.toml")

    # API Health Ping
    with st.expander("⚡ API Diagnostics", expanded=False):
        if st.button("Ping Gemini API", use_container_width=True):
            with st.spinner("Testing connectivity..."):
                health = check_api_health(active_key, gemini_model)
                if health["status"] == "success":
                    st.success(f"Connected! Latency: {health['latency_ms']}ms")
                else:
                    st.error(f"Error: {health.get('message', 'Unknown error')}")


# -----------------------------------------------------------------------------
# 7. Document Ingestion Pipeline
# -----------------------------------------------------------------------------
if uploaded_files:
    file_sig = "_".join(f"{f.name}_{len(f.getvalue())}" for f in uploaded_files)
    if st.session_state.get("active_file_sig") != file_sig:
        with st.spinner(f"Ingesting & indexing {len(uploaded_files)} document(s)..."):
            t0 = time.time()
            all_pages: List[Dict[str, Any]] = []
            for f in uploaded_files:
                pages = parse_single_file(f.getvalue(), f.name, active_key, gemini_model)
                all_pages.extend(pages)

            if not all_pages:
                st.error("Could not extract readable text from the uploaded files.")
                st.stop()

            chunks = build_chunks(all_pages, chunk_size=650, overlap=100)
            vec, mat = build_search_index(chunks)

            st.session_state["active_file_sig"] = file_sig
            st.session_state["chunks"] = chunks
            st.session_state["search_vec"] = vec
            st.session_state["search_mat"] = mat
            st.session_state["doc_count"] = len(uploaded_files)
            st.session_state["file_names"] = [f.name for f in uploaded_files]


# -----------------------------------------------------------------------------
# 8. Main Chat Workspace
# -----------------------------------------------------------------------------
chunks = st.session_state.get("chunks", [])
vec = st.session_state.get("search_vec")
mat = st.session_state.get("search_mat")
doc_count = st.session_state.get("doc_count", 0)

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Top Workspace Bar
if chunks:
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; border-radius: 12px; background: {t_bg_card}; border: 1px solid {t_border}; margin-bottom: 16px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.1rem;">📚</span>
            <span style="font-size: 0.86rem; font-weight: 600; color: {t_text_primary};">{doc_count} File(s) Indexed</span>
            <span style="font-size: 0.76rem; color: {t_text_secondary};">({len(chunks)} Chunks)</span>
        </div>
        <div style="display: flex; gap: 6px;">
            <span class="pill-badge">🤖 {gemini_model}</span>
            <span class="pill-badge">{retrieval_mode.split()[0]} {retrieval_mode.split()[1] if len(retrieval_mode.split()) > 1 else ''}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Centered Landing Welcome Screen when Empty
if not st.session_state["messages"]:
    st.markdown(f"""
    <div class="welcome-container">
        <div class="welcome-logo">✨</div>
        <div class="welcome-title">What would you like to know from your documents?</div>
        <div class="welcome-sub">Ask questions across PDF, Word, Excel, CSV, and Markdown with source citations and Corrective RAG verification.</div>
    </div>
    """, unsafe_allow_html=True)

    if doc_count == 0:
        st.info("💡 Upload one or more documents in the left sidebar to enable source-grounded answers.")

    # 4 Quick Prompt Cards
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📌 Summarize core findings and conclusions", use_container_width=True):
            st.session_state["quick_prompt"] = "Summarize the key findings, main arguments, and conclusions across the uploaded documents."
        if st.button("⚖️ Compare claims and metrics side-by-side", use_container_width=True):
            st.session_state["quick_prompt"] = "Compare the key findings, methodologies, and metrics across the uploaded documents."
    with c2:
        if st.button("📊 Extract quantitative tables & data", use_container_width=True):
            st.session_state["quick_prompt"] = "Extract all key quantitative figures, tables, and performance metrics from the documents."
        if st.button("❓ What are the main limitations or risks?", use_container_width=True):
            st.session_state["quick_prompt"] = "What limitations, security risks, or challenges are highlighted in these documents?"


# Render Conversation Messages
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="✨"):
            st.markdown(msg["content"])

            # Citations Accordion
            if msg.get("citations"):
                with st.expander(f"📚 Verified Sources ({len(msg['citations'])})", expanded=False):
                    for idx, cit in enumerate(msg["citations"], start=1):
                        st.markdown(f"""
                        <div style="padding: 8px 12px; margin-bottom: 6px; border-radius: 8px; background: {t_input_bg}; border: 1px solid {t_border}; font-size: 0.82rem;">
                            <div style="font-weight: 600; color: {t_accent}; margin-bottom: 2px;">Source {idx}: {cit['label']}</div>
                            <div style="color: {t_text_secondary}; line-height: 1.4;">{cit['text'][:320]}...</div>
                        </div>
                        """, unsafe_allow_html=True)

            # CRAG Diagnostic Trace
            if msg.get("crag_trace") and msg["crag_trace"].get("rewritten_queries"):
                with st.expander("🛡️ Corrective RAG (CRAG) Search Expansion Trace", expanded=False):
                    st.caption("Initial query had weak semantic alignment. Corrective RAG expanded queries:")
                    for rq in msg["crag_trace"]["rewritten_queries"]:
                        st.code(f"Expanded: \"{rq}\"", language=None)

            # Metadata Footer
            st.caption(f"⚡ Latency: **{msg.get('latency', 0.0):.2f}s** • 🤖 Model: **{msg.get('model', gemini_model)}** • 🛡️ Mode: **{msg.get('mode', 'RAG')}**")


# Bottom Chat Composer
user_input = st.chat_input("Ask anything about your documents...")

if st.session_state.get("quick_prompt"):
    user_input = st.session_state.pop("quick_prompt")

if user_input and user_input.strip():
    st.session_state["messages"].append({"role": "user", "content": user_input})

    with st.spinner("Analyzing documents & generating grounded response..."):
        t_start = time.time()
        citations = []
        crag_trace = None

        if chunks and vec is not None and mat is not None:
            # 1. Initial Retrieval Pass
            ranked = search_chunks(user_input, chunks, vec, mat, top_k=top_k)
            top_score = ranked[0][1] if ranked else 0.0

            crag_trace = {
                "mode": retrieval_mode,
                "top_score": top_score,
                "rewritten_queries": []
            }

            # 2. Corrective RAG Retry Loop when score is low or ambiguous
            if "Corrective" in retrieval_mode and (top_score < 0.28 or len(ranked) < 2):
                rewrites = expand_query_for_crag(user_input)
                crag_trace["rewritten_queries"] = rewrites
                seen_texts = {c[0]["text"] for c in ranked}
                for rq in rewrites:
                    extra = search_chunks(rq, chunks, vec, mat, top_k=top_k)
                    for ch, sc in extra:
                        if ch["text"] not in seen_texts:
                            ranked.append((ch, sc))
                            seen_texts.add(ch["text"])
                ranked.sort(key=lambda x: x[1], reverse=True)
                ranked = ranked[:top_k]

            evidence_blocks = []
            for i, (c, sc) in enumerate(ranked, start=1):
                citations.append({"label": c["label"], "text": c["text"], "score": sc})
                evidence_blocks.append(f"<source id=\"Source {i}\" location=\"{c['label']}\">\n{c['text']}\n</source>")

            if active_key:
                final_answer = execute_llm_generation(
                    user_input,
                    evidence_blocks,
                    active_key,
                    gemini_model,
                    retrieval_mode
                )
            else:
                final_answer = "⚠️ Server GEMINI_API_KEY is not configured. Please add it to .streamlit/secrets.toml."
        else:
            final_answer = "⚠️ Please upload one or more documents in the left sidebar to enable grounded document analysis."

        t_elapsed = time.time() - t_start

        st.session_state["messages"].append({
            "role": "assistant",
            "content": final_answer,
            "citations": citations,
            "crag_trace": crag_trace,
            "latency": t_elapsed,
            "model": gemini_model,
            "mode": retrieval_mode
        })
        st.rerun()
