"""
=============================================================================
🩸 NeuralRAG Studio: Dual-Theme Multimodal AI Laboratory
=============================================================================
A modern ChatGPT-style Crimson, Slate & Light/Dark RAG platform:
1. Dual Theme System: Instant Color Switch with Clickable Buttons (🌙 Dark & ☀️ Light)
2. Protected Primary API Engine: Solely uses host/user's primary key; never exposed
3. Built-in API Error Diagnostics: Live health testing, latency check & error breakdown
4. Universal Multi-Format Ingestion: PDF (Digital + Scanned OCR), Word (.docx + Diagrams),
   Excel (.xlsx, .csv Tabular RAG + DataFrames), and Images (Gemini Multimodal OCR)
5. Powered by Google Gemini 3.1 Flash Lite as the primary LLM engine
6. Dense Neural Vectors (MiniLM) vs. Sparse TF-IDF Lexical Retrieval
7. Interactive Tools: Content & OCR Preview, Chunk Inspector, Analytics & Downloads
=============================================================================
"""

import os
import re
import time
import base64
from io import BytesIO
from typing import List, Dict, Any, Tuple

import streamlit as st
import numpy as np
import pypdf
import requests
from PIL import Image

# Graceful optional imports
try:
    import docx
except ImportError:
    docx = None

try:
    import pandas as pd
except ImportError:
    pd = None


# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NeuralRAG Studio | Multimodal AI Laboratory",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Theme State & Dynamic Dual-Theme CSS (Buttons for Dark & Light Mode)
# -----------------------------------------------------------------------------
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

is_dark = (st.session_state["theme_mode"] == "dark")

# Dynamic theme color palette
if is_dark:
    t_bg_app = "#0b0d14"
    t_bg_sidebar = "#111420"
    t_bg_card = "#161a29"
    t_border_card = "rgba(225, 29, 72, 0.24)"
    t_text_primary = "#f8fafc"
    t_text_secondary = "#94a3b8"
    t_accent = "#f43f5e"
    t_accent_glow = "rgba(244, 63, 94, 0.25)"
    t_bubble_user_bg = "rgba(225, 29, 72, 0.16)"
    t_bubble_user_border = "rgba(225, 29, 72, 0.38)"
    t_bubble_user_text = "#ffffff"
    t_bubble_asst_bg = "#151825"
    t_bubble_asst_border = "rgba(255, 255, 255, 0.08)"
    t_bubble_asst_text = "#f1f5f9"
    t_citation_bg = "#121520"
    t_citation_border = "rgba(225, 29, 72, 0.3)"
    t_citation_text = "#e2e8f0"
    t_input_bg = "#141726"
    t_input_border = "rgba(225, 29, 72, 0.35)"
    t_tab_bg = "rgba(20, 24, 36, 0.7)"
    t_tab_active_bg = "rgba(225, 29, 72, 0.22)"
    t_tab_active_text = "#ffffff"
    t_tab_inactive_text = "#94a3b8"
    t_metric_bg = "rgba(225, 29, 72, 0.15)"
    t_metric_border = "rgba(225, 29, 72, 0.3)"
    t_metric_text = "#fecdd3"
    t_card_shadow = "0 4px 20px rgba(0, 0, 0, 0.45)"
    t_btn_bg = "#171b2b"
    t_btn_text = "#f8fafc"
    t_btn_border = "rgba(225, 29, 72, 0.3)"
    t_uploader_bg = "#141726"
    t_uploader_border = "rgba(225, 29, 72, 0.35)"
    t_uploader_hover = "rgba(225, 29, 72, 0.12)"
else:
    t_bg_app = "#f8fafc"
    t_bg_sidebar = "#ffffff"
    t_bg_card = "#ffffff"
    t_border_card = "#e2e8f0"
    t_text_primary = "#0f172a"
    t_text_secondary = "#475569"
    t_accent = "#e11d48"
    t_accent_glow = "rgba(225, 29, 72, 0.12)"
    t_bubble_user_bg = "#fff1f2"
    t_bubble_user_border = "#fecdd3"
    t_bubble_user_text = "#881337"
    t_bubble_asst_bg = "#ffffff"
    t_bubble_asst_border = "#e2e8f0"
    t_bubble_asst_text = "#0f172a"
    t_citation_bg = "#f8fafc"
    t_citation_border = "#e2e8f0"
    t_citation_text = "#1e293b"
    t_input_bg = "#ffffff"
    t_input_border = "#cbd5e1"
    t_tab_bg = "#f1f5f9"
    t_tab_active_bg = "#fff1f2"
    t_tab_active_text = "#e11d48"
    t_tab_inactive_text = "#64748b"
    t_metric_bg = "#fff1f2"
    t_metric_border = "#fecdd3"
    t_metric_text = "#9f1239"
    t_card_shadow = "0 4px 16px rgba(0, 0, 0, 0.05)"
    t_btn_bg = "#ffffff"
    t_btn_text = "#0f172a"
    t_btn_border = "#e2e8f0"
    t_uploader_bg = "#f8fafc"
    t_uploader_border = "#cbd5e1"
    t_uploader_hover = "#fff1f2"

# Inject High-Contrast Dynamic CSS
st.markdown(f"""
<style>
    /* 1. Complete Removal of Top Deploy Button & Toolbar */
    .stAppDeployButton,
    [data-testid="stAppDeployButton"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"],
    #MainMenu,
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        width: 0px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}
    .block-container {{
        padding-top: 1.8rem !important;
        padding-bottom: 3.5rem !important;
    }}

    /* 2. Global Canvas & Typography */
    .stApp {{
        background-color: {t_bg_app} !important;
        color: {t_text_primary} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    
    /* 3. Sidebar Full Blackout & Header Fix */
    section[data-testid="stSidebar"],
    [data-testid="stSidebarHeader"],
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"],
    [data-testid="stSidebarNav"] {{
        background-color: {t_bg_sidebar} !important;
        border-right: 1px solid {t_border_card} !important;
        color: {t_text_primary} !important;
    }}
    [data-testid="stSidebarHeader"] {{
        background-color: {t_bg_sidebar} !important;
        border-bottom: 1px solid {t_border_card} !important;
        padding: 0.5rem 1rem !important;
    }}
    [data-testid="stSidebarCollapseButton"] button {{
        color: {t_text_primary} !important;
    }}
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {{
        color: {t_text_primary} !important;
    }}
    
    /* 4. Universal File Uploader Styling (Eliminate White Areas) */
    [data-testid="stFileUploader"],
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploadDropzone"],
    [data-testid="stFileUploaderDropzone"],
    section[data-testid="stFileUploadDropzone"],
    div[data-testid="stFileUploaderDropzone"] {{
        background-color: {t_uploader_bg} !important;
        border: 1px dashed {t_uploader_border} !important;
        border-radius: 10px !important;
        color: {t_text_primary} !important;
    }}
    [data-testid="stFileUploader"] section:hover,
    [data-testid="stFileUploadDropzone"]:hover {{
        border-color: {t_accent} !important;
        background-color: {t_uploader_hover} !important;
    }}
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploadDropzone"] small,
    [data-testid="stFileUploadDropzone"] span {{
        color: {t_text_secondary} !important;
    }}
    [data-testid="stFileUploader"] button {{
        background-color: {t_btn_bg} !important;
        color: {t_btn_text} !important;
        border: 1px solid {t_btn_border} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stFileUploader"] button:hover {{
        border-color: {t_accent} !important;
        color: {t_accent} !important;
    }}

    /* 5. Sticky Bottom Chat Input Box (Eliminate White Input) */
    div[data-testid="stChatInput"] {{
        background-color: {t_input_bg} !important;
        border: 1px solid {t_input_border} !important;
        border-radius: 14px !important;
        box-shadow: {t_card_shadow} !important;
        padding: 2px !important;
    }}
    div[data-testid="stChatInput"] > div {{
        background-color: {t_input_bg} !important;
        border: none !important;
        border-radius: 12px !important;
    }}
    div[data-testid="stChatInput"] textarea {{
        background-color: transparent !important;
        color: {t_text_primary} !important;
        font-size: 0.95rem !important;
    }}
    div[data-testid="stChatInput"] textarea::placeholder {{
        color: {t_text_secondary} !important;
        opacity: 0.8 !important;
    }}
    div[data-testid="stChatInput"] button {{
        background-color: {t_accent} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stChatInput"] button:hover {{
        background-color: #be123c !important;
    }}

    /* 6. Form Inputs, Selectboxes, Text Areas & Expanders */
    .stTextInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stTextArea textarea {{
        color: {t_text_primary} !important;
        background-color: {t_input_bg} !important;
        border: 1px solid {t_input_border} !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stExpander"] {{
        background-color: {t_bg_card} !important;
        border: 1px solid {t_border_card} !important;
        border-radius: 10px !important;
    }}
    div[data-testid="stExpander"] details {{
        background-color: transparent !important;
    }}
    div[data-testid="stExpander"] summary {{
        color: {t_text_primary} !important;
    }}

    /* 7. Top Brand Header */
    .brand-header {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 0 14px 0;
        border-bottom: 1px solid {t_border_card};
        margin-bottom: 14px;
    }}
    .brand-logo {{
        font-size: 1.85rem;
    }}
    .brand-name {{
        font-size: 1.35rem;
        font-weight: 800;
        color: {t_text_primary};
        letter-spacing: -0.02em;
    }}
    .brand-name span {{
        color: {t_accent};
    }}

    /* 8. Welcome Container */
    .welcome-container {{
        max-width: 780px;
        margin: 28px auto 20px auto;
        text-align: center;
    }}
    .welcome-logo {{
        width: 64px;
        height: 64px;
        line-height: 64px;
        border-radius: 50%;
        background: {t_accent_glow};
        border: 2px solid {t_accent};
        font-size: 2rem;
        margin: 0 auto 16px auto;
        box-shadow: 0 0 24px {t_accent_glow};
    }}
    .welcome-title {{
        font-size: 1.9rem;
        font-weight: 750;
        color: {t_text_primary};
        margin-bottom: 8px;
        letter-spacing: -0.01em;
    }}
    .welcome-sub {{
        font-size: 1.0rem;
        color: {t_text_secondary};
        margin-bottom: 24px;
        line-height: 1.5;
    }}
    
    /* 9. Prompt suggestion cards & Streamlit Buttons */
    div[data-testid="stButton"] button {{
        background-color: {t_btn_bg} !important;
        color: {t_btn_text} !important;
        border: 1px solid {t_btn_border} !important;
        border-radius: 10px !important;
        padding: 10px 16px !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stButton"] button:hover {{
        border-color: {t_accent} !important;
        color: {t_accent} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px {t_accent_glow};
    }}
    
    /* 10. Chat Messages */
    div[data-testid="stChatMessage"] {{
        background-color: {t_bubble_asst_bg} !important;
        border: 1px solid {t_bubble_asst_border} !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        color: {t_bubble_asst_text} !important;
        box-shadow: {t_card_shadow} !important;
    }}
    
    /* 11. Citation Cards */
    .citation-card {{
        background: {t_citation_bg};
        border-left: 3px solid {t_accent};
        border-top: 1px solid {t_border_card};
        border-right: 1px solid {t_border_card};
        border-bottom: 1px solid {t_border_card};
        border-radius: 8px;
        padding: 12px 14px;
        margin-top: 8px;
        font-size: 0.88rem;
        color: {t_citation_text};
        line-height: 1.5;
    }}
    
    /* 12. Metric Pills */
    .metric-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: {t_metric_bg};
        border: 1px solid {t_metric_border};
        border-radius: 9999px;
        padding: 4px 12px;
        font-size: 0.78rem;
        font-weight: 600;
        color: {t_metric_text};
    }}
    
    /* 13. Streamlit Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: 1px solid {t_border_card};
        margin-bottom: 18px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {t_tab_bg};
        border-radius: 8px 8px 0 0;
        color: {t_tab_inactive_text};
        font-weight: 600;
        padding: 8px 18px;
        border: 1px solid transparent;
        font-size: 0.9rem;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {t_tab_active_bg} !important;
        color: {t_tab_active_text} !important;
        border: 1px solid {t_border_card} !important;
        border-bottom: 2px solid {t_accent} !important;
    }}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 3. Dense Embedding Model Loader
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Initializing neural embeddings (all-MiniLM-L6-v2)…")
def get_dense_embedder():
    """Loads SentenceTransformers model if available, else returns None."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception:
        return None


# -----------------------------------------------------------------------------
# 4. Protected Primary API Key Engine & Diagnostics
# -----------------------------------------------------------------------------
def get_primary_api_key() -> Tuple[str, str]:
    """
    Exclusively retrieves the primary Gemini API key from secrets or environment.
    Guarantees the dashboard only uses the host/user's primary key and NEVER displays it.
    """
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


def check_gemini_api_health(api_key: str, model: str = "gemini-3.1-flash-lite") -> Dict[str, Any]:
    """
    Performs a live connectivity and error diagnostic check against Google Gemini.
    Returns status code, latency, error reason, and practical resolution advice.
    """
    if not api_key:
        return {
            "status": "error",
            "code": 401,
            "message": "GEMINI_API_KEY is not configured.",
            "latency_ms": 0,
            "remedy": "Add GEMINI_API_KEY to .streamlit/secrets.toml or set the GEMINI_API_KEY environment variable."
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    payload = {
        "contents": [{"parts": [{"text": "Health check ping. Reply with OK."}]}],
        "generationConfig": {"maxOutputTokens": 10, "temperature": 0.0}
    }

    t0 = time.time()
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=12)
        latency_ms = int((time.time() - t0) * 1000)

        if res.status_code == 200:
            return {
                "status": "success",
                "code": 200,
                "message": f"Successfully connected to Google Gemini API ({model})!",
                "latency_ms": latency_ms,
                "model": model,
                "remedy": None
            }
        else:
            err_msg = res.text
            err_status = ""
            try:
                err_json = res.json().get("error", {})
                err_msg = err_json.get("message", res.text)
                err_status = err_json.get("status", "")
            except Exception:
                pass

            remedy = "Verify key status in Google AI Studio console."
            if res.status_code == 400:
                remedy = "Invalid request format or model parameter. Verify model name."
            elif res.status_code in (401, 403):
                remedy = "API key is invalid, inactive, or unauthorized. Verify the key string in .streamlit/secrets.toml."
            elif res.status_code == 404:
                remedy = f"Model '{model}' is not available or has been retired. Please select 'gemini-3.1-flash-lite' or 'gemini-3.5-flash'."
            elif res.status_code == 429:
                remedy = "Quota limit reached (Rate Limit Exceeded). Please wait 30-60 seconds before making more requests."
            elif res.status_code in (500, 503):
                remedy = "Google Gemini servers are temporarily experiencing high traffic. Please retry in a few moments."

            return {
                "status": "error",
                "code": res.status_code,
                "status_str": err_status,
                "message": err_msg,
                "latency_ms": latency_ms,
                "model": model,
                "remedy": remedy
            }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "code": 408,
            "message": "Connection timed out after 12 seconds while connecting to Google Gemini servers.",
            "latency_ms": int((time.time() - t0) * 1000),
            "remedy": "Check your local internet connection, firewall, or proxy settings."
        }
    except Exception as exc:
        return {
            "status": "error",
            "code": "NetworkError",
            "message": str(exc),
            "latency_ms": int((time.time() - t0) * 1000),
            "remedy": "Network or DNS resolution failure. Check internet connectivity."
        }


# -----------------------------------------------------------------------------
# 5. Top-Notch Multimodal OCR & Document Parsers (PDF, Word, Excel, CSV, Images)
# -----------------------------------------------------------------------------
def perform_gemini_ocr(image_bytes: bytes, mime_type: str, api_key: str, model: str = "gemini-3.1-flash-lite") -> str:
    """
    Advanced Multimodal Vision OCR transcribing documents, scanned pages, charts,
    diagrams, and tables with Google Gemini.
    """
    if not api_key:
        return "[Image detected. Configure Gemini API Key to enable AI Vision OCR transcription.]"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "You are an expert Multimodal Document & Vision OCR Engine.\n"
        "Your task is to transcribe this document image with maximum fidelity:\n"
        "1. Text & Headings: Transcribe all visible text, titles, subtitles, headers, and bullet points verbatim.\n"
        "2. Tables: Convert any tabular data into clean Markdown tables with header rows.\n"
        "3. Diagrams & Charts: If there are graphs, bar charts, flowcharts, or architecture diagrams, extract all data points, labels, axes, legends, and key takeaways into structured bullet points.\n"
        "4. Math & Formulas: Preserve mathematical formulas and technical notation.\n"
        "5. Structure: Maintain natural document hierarchy. Do not summarize or omit small details."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": mime_type, "data": b64_data}}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000}
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=35)
        if res.status_code == 200:
            candidates = res.json().get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                return text or "[OCR returned empty text]"
            return "[OCR returned no candidate text]"
        else:
            err_msg = res.text
            try:
                err_msg = res.json().get("error", {}).get("message", res.text)
            except Exception:
                pass
            return f"[OCR Error ({res.status_code}): {err_msg}]"
    except requests.exceptions.Timeout:
        return "[OCR Error: Request timed out after 35 seconds]"
    except Exception as exc:
        return f"[OCR Network Error: {str(exc)}]"


def parse_pdf(file_bytes: bytes, api_key: str = "", model: str = "gemini-3.1-flash-lite") -> Tuple[str, List[Dict[str, Any]]]:
    """
    State-of-the-art PDF reader:
    - Extracts native digital text per page.
    - Automatically detects scanned/image-only pages (< 50 chars) and transcribes with Gemini OCR.
    - If a digital page has embedded charts/diagrams, also extracts and transcribes visual charts!
    """
    reader = pypdf.PdfReader(BytesIO(file_bytes))
    page_records = []
    full_text_list = []

    for i, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""

        cleaned = " ".join(page_text.split())
        has_ocr = False

        # Scanned page OCR check
        if len(cleaned) < 50 and hasattr(page, "images") and len(page.images) > 0 and api_key:
            try:
                first_img = page.images[0]
                img_ocr = perform_gemini_ocr(first_img.data, "image/png", api_key, model=model)
                if img_ocr and not img_ocr.startswith("[OCR Error"):
                    cleaned = f"(OCR Transcribed Scanned Page)\n{img_ocr}"
                    has_ocr = True
            except Exception:
                pass
        # Digital page with embedded diagram check
        elif hasattr(page, "images") and len(page.images) > 0 and api_key and len(cleaned) >= 50:
            try:
                img_candidate = page.images[0]
                # If image is reasonably large (> 10KB), it could be a diagram or chart
                if len(img_candidate.data) > 10000:
                    diag_ocr = perform_gemini_ocr(img_candidate.data, "image/png", api_key, model=model)
                    if diag_ocr and not diag_ocr.startswith("[OCR"):
                        cleaned += f"\n\n[Visual Diagram / Chart OCR Extracted from Page {i}]:\n{diag_ocr}"
                        has_ocr = True
            except Exception:
                pass

        if cleaned:
            page_records.append({
                "page_num": i,
                "label": f"Page {i}" + (" (OCR Transcribed)" if has_ocr else ""),
                "text": cleaned,
                "char_count": len(cleaned)
            })
            full_text_list.append(f"[Page {i}]\n{cleaned}")

    return "\n\n".join(full_text_list), page_records


def parse_word(file_bytes: bytes, api_key: str = "", model: str = "gemini-3.1-flash-lite") -> Tuple[str, List[Dict[str, Any]]]:
    """
    Top-notch Word Document reader (.docx):
    - Headings with hierarchy levels (# Heading 1, ## Heading 2).
    - Paragraphs and bullet points.
    - Tables extracted with Markdown table structure (headers preserved).
    - Embedded figures and diagrams extracted and transcribed via Gemini OCR!
    """
    if docx is None:
        return "python-docx library not installed.", []

    doc = docx.Document(BytesIO(file_bytes))
    page_records = []
    full_text_list = []
    current_section = []
    sec_idx = 1

    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue

        # Preserve heading levels
        if p.style and p.style.name and "heading" in p.style.name.lower():
            txt = f"\n### {txt}\n"

        current_section.append(txt)
        if len("\n".join(current_section)) > 750:
            sec_text = "\n".join(current_section)
            page_records.append({
                "page_num": sec_idx,
                "label": f"Section {sec_idx}",
                "text": sec_text,
                "char_count": len(sec_text)
            })
            full_text_list.append(f"[Section {sec_idx}]\n{sec_text}")
            sec_idx += 1
            current_section = []

    # Extract tables formatted as Markdown tables
    for t_idx, table in enumerate(doc.tables, start=1):
        if not table.rows:
            continue

        table_lines = []
        headers = [c.text.strip().replace("\n", " ") for c in table.rows[0].cells]
        table_lines.append("| " + " | ".join(headers) + " |")
        table_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for row in table.rows[1:]:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            table_lines.append("| " + " | ".join(cells) + " |")

        tbl_text = f"\nTable {t_idx} (Data Grid):\n" + "\n".join(table_lines) + "\n"
        current_section.append(tbl_text)

    # Embedded images OCR in Word documents
    if api_key and hasattr(doc, "part") and hasattr(doc.part, "rels"):
        try:
            for rel in doc.part.rels.values():
                if "image" in getattr(rel, "target_ref", ""):
                    img_data = rel.target_part.blob
                    if len(img_data) > 8000:
                        img_ocr = perform_gemini_ocr(img_data, "image/png", api_key, model=model)
                        if img_ocr and not img_ocr.startswith("[OCR"):
                            current_section.append(f"\n[Embedded Word Document Figure OCR]:\n{img_ocr}\n")
                            break
        except Exception:
            pass

    if current_section:
        sec_text = "\n".join(current_section)
        page_records.append({
            "page_num": sec_idx,
            "label": f"Section {sec_idx}",
            "text": sec_text,
            "char_count": len(sec_text)
        })
        full_text_list.append(f"[Section {sec_idx}]\n{sec_text}")

    return "\n\n".join(full_text_list), page_records


def df_to_markdown_grid(df: Any, max_rows: int = 40) -> str:
    """Converts a pandas DataFrame into a structured Markdown grid."""
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, r in df.head(max_rows).iterrows():
        row_str = "| " + " | ".join(str(val).replace("\n", " ").strip() for val in r.values) + " |"
        rows.append(row_str)
    return "\n".join([header, sep] + rows)


def parse_excel_or_csv(file_bytes: bytes, filename: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Enterprise-grade Spreadsheet parser (.xlsx, .xls, .csv):
    - Reads all sheets.
    - Generates summary statistics (row/col counts, numeric averages, sums).
    - Converts data rows into structured Markdown tables with header context.
    - Slices large sheets into groups of 25-30 rows, repeating headers on every chunk
      so RAG vector search retains column-to-value context!
    """
    if pd is None:
        return "pandas library not installed.", [], {}

    page_records = []
    full_text_list = []
    sheet_dataframes = {}

    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(BytesIO(file_bytes))
            sheet_dataframes = {"CSV_Data": df}
        else:
            sheet_dataframes = pd.read_excel(BytesIO(file_bytes), sheet_name=None)

        sec_counter = 1
        for sheet_name, df_sheet in sheet_dataframes.items():
            df_clean = df_sheet.dropna(how="all")
            total_rows, total_cols = df_clean.shape
            col_list = list(df_clean.columns)

            # Build statistical summary
            num_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
            stat_summary = ""
            if num_cols:
                stats = []
                for nc in num_cols[:4]:
                    col_mean = df_clean[nc].mean()
                    col_sum = df_clean[nc].sum()
                    stats.append(f"'{nc}' (Avg: {col_mean:.2f}, Sum: {col_sum:.2f})")
                stat_summary = f"Numeric Column Metrics: {', '.join(stats)}\n"

            sheet_header = (
                f"### Spreadsheet Sheet: {sheet_name}\n"
                f"**Dimensions:** {total_rows} rows × {total_cols} columns\n"
                f"**Columns:** {', '.join(str(c) for c in col_list)}\n"
                f"{stat_summary}\n"
            )

            # Chunk by groups of 25 rows to preserve tabular context
            step = 25
            if total_rows == 0:
                content = sheet_header + "*(Empty Sheet)*"
                page_records.append({
                    "page_num": sec_counter,
                    "label": f"Sheet: {sheet_name}",
                    "text": content,
                    "char_count": len(content)
                })
                full_text_list.append(content)
                sec_counter += 1
            else:
                for start_idx in range(0, total_rows, step):
                    end_idx = min(start_idx + step, total_rows)
                    df_slice = df_clean.iloc[start_idx:end_idx]
                    table_md = df_to_markdown_grid(df_slice, max_rows=step)
                    chunk_text = (
                        f"{sheet_header}"
                        f"**Rows [{start_idx + 1} - {end_idx}] Data Table:**\n"
                        f"{table_md}"
                    )
                    page_records.append({
                        "page_num": sec_counter,
                        "label": f"Sheet: {sheet_name} (Rows {start_idx + 1}-{end_idx})",
                        "text": chunk_text,
                        "char_count": len(chunk_text)
                    })
                    full_text_list.append(chunk_text)
                    sec_counter += 1

    except Exception as exc:
        err = f"Spreadsheet read error: {str(exc)}"
        return err, [{"page_num": 1, "label": "Error", "text": err, "char_count": len(err)}], {}

    return "\n\n".join(full_text_list), page_records, sheet_dataframes


def parse_image_file(file_bytes: bytes, filename: str, api_key: str, model: str = "gemini-3.1-flash-lite") -> Tuple[str, List[Dict[str, Any]]]:
    """
    High-fidelity Multimodal Image Reader:
    Transcribes text, charts, diagrams, infographics, and receipts via Gemini Vision OCR.
    """
    mime = "image/png"
    lower_name = filename.lower()
    if lower_name.endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    elif lower_name.endswith(".webp"):
        mime = "image/webp"

    ocr_txt = perform_gemini_ocr(file_bytes, mime, api_key, model=model)
    page_records = [{
        "page_num": 1,
        "label": f"Image: {filename} (Multimodal Vision OCR)",
        "text": ocr_txt,
        "char_count": len(ocr_txt)
    }]
    return f"[Multimodal AI Vision OCR: {filename}]\n{ocr_txt}", page_records


def universal_document_loader(uploaded_file, api_key: str = "", model: str = "gemini-3.1-flash-lite") -> Tuple[str, List[Dict[str, Any]], str, Dict[str, Any]]:
    """Universal document loader returning (full_text, page_records, detected_type, auxiliary_data)."""
    file_bytes = uploaded_file.getvalue()
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        t, p = parse_pdf(file_bytes, api_key=api_key, model=model)
        return t, p, "PDF Document (Digital & OCR)", {}
    elif name.endswith(".docx"):
        t, p = parse_word(file_bytes, api_key=api_key, model=model)
        return t, p, "Word Document (.docx + Diagrams)", {}
    elif name.endswith((".xlsx", ".xls", ".csv")):
        t, p, dfs = parse_excel_or_csv(file_bytes, uploaded_file.name)
        return t, p, "Excel/CSV Spreadsheet (Tabular RAG)", {"dfs": dfs}
    elif name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        t, p = parse_image_file(file_bytes, uploaded_file.name, api_key=api_key, model=model)
        return t, p, "Image (Multimodal Vision OCR)", {"image_bytes": file_bytes}
    else:
        raw = file_bytes.decode("utf-8", errors="ignore")
        cleaned = " ".join(raw.split())
        return cleaned, [{"page_num": 1, "label": "Plain Text", "text": cleaned, "char_count": len(cleaned)}], "Plain Text", {}


# -----------------------------------------------------------------------------
# 6. Overlapping Chunking & Vector Search
# -----------------------------------------------------------------------------
def build_chunks(page_records: List[Dict[str, Any]], chunk_size: int = 650, overlap: int = 120) -> List[Dict[str, Any]]:
    """Partitions text into overlapping character spans while preserving section labels."""
    chunks = []
    chunk_counter = 1

    for record in page_records:
        text = record["text"]
        label = record.get("label", f"Page {record['page_num']}")
        if not text:
            continue

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            content = text[start:end].strip()
            if content:
                chunks.append({
                    "chunk_id": chunk_counter,
                    "page_num": record["page_num"],
                    "label": label,
                    "text": content,
                    "char_len": len(content),
                    "start_char": start,
                    "end_char": end
                })
                chunk_counter += 1
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)

    return chunks


def index_chunks(chunks: List[Dict[str, Any]], method: str = "Dense Neural (MiniLM)") -> Tuple[Any, Any, Any]:
    """Builds Dense or Sparse index representation."""
    texts = [c["text"] for c in chunks]
    if method.startswith("Dense Neural"):
        embedder = get_dense_embedder()
        if embedder is not None:
            vectors = embedder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
            return ("dense", embedder, vectors)
        else:
            method = "Sparse TF-IDF"

    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    mat = vec.fit_transform(texts)
    return ("tfidf", vec, mat)


def perform_retrieval(query: str, chunks: List[Dict[str, Any]], index_payload: Tuple[Any, Any, Any], top_k: int = 4):
    """Computes cosine similarity ranking."""
    idx_type, model_obj, vec_data = index_payload
    if idx_type == "dense":
        q_vec = model_obj.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = vec_data @ q_vec
    else:
        from sklearn.metrics.pairwise import cosine_similarity
        q_vec = model_obj.transform([query])
        scores = cosine_similarity(q_vec, vec_data)[0]

    top_idx = np.argsort(scores)[::-1][:min(top_k, len(chunks))]
    return [(chunks[int(i)], float(scores[int(i)])) for i in top_idx]


# -----------------------------------------------------------------------------
# 7. Grounded Generation Pipeline & Detailed API Error Handling
# -----------------------------------------------------------------------------
def call_gemini_llm(query: str, context: str, api_key: str, model: str = "gemini-3.1-flash-lite", temperature: float = 0.0) -> str:
    """
    Airtight, zero-hallucination RAG generator via Google Gemini with detailed error reporting:
    - Strictly answers ONLY using facts present in the provided document passages.
    - If information is not in the text, explicitly states so without speculating.
    - Captures and reports exact HTTP status codes, error messages, and remediation tips.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    low_q = query.lower()
    external_triggers = [
        "extra info", "outside info", "beyond the document", "external info",
        "outside knowledge", "more than the document", "general knowledge",
        "explain further outside", "additional info beyond", "external information",
        "what else do you know", "beyond this document"
    ]
    user_requested_extra = any(trigger in low_q for trigger in external_triggers)

    if user_requested_extra:
        system_instruction_text = (
            "You are an expert AI teaching assistant operating in Retrieval-Augmented Generation mode.\n"
            "The user has explicitly asked for additional external information beyond the uploaded document.\n"
            "STRUCTURE YOUR ANSWER CAREFULLY:\n"
            "1. **### Document Grounded Answer**: First answer strictly based on the provided document passages.\n"
            "2. **### External Knowledge (Beyond Document)**: Then provide the requested outside information under this separate heading.\n"
            "Always clearly distinguish between what is directly in the document and what comes from outside."
        )
    else:
        system_instruction_text = (
            "You are a strict, zero-hallucination AI teaching assistant operating in Retrieval-Augmented Generation mode.\n"
            "CRITICAL OPERATIONAL RULES:\n"
            "1. SOLE SOURCE OF TRUTH: Answer strictly, exclusively, and faithfully using ONLY facts directly stated in the provided context passages.\n"
            "2. ZERO UNSOLICITED KNOWLEDGE: Do NOT introduce external facts, general knowledge, outside commentary, or speculative assumptions from your pre-training memory. If a fact is not stated in the passages, IT DOES NOT EXIST.\n"
            "3. NO EXTRA INFORMATION: Answer ONLY what was explicitly asked. Do NOT provide unsolicited background, related topics, or extra explanations.\n"
            "4. MISSING INFORMATION RULE: If the answer cannot be found in the provided context passages, respond strictly with:\n"
            "'The uploaded document does not contain information to answer this question.' Do not attempt to guess or answer partially.\n"
            "5. CITATIONS: Cite the specific Passage # and Page/Section/Sheet number supporting your response whenever available."
        )

    user_prompt = (
        f"=== CONTEXT PASSAGES FROM UPLOADED DOCUMENT ===\n{context}\n\n"
        f"=== USER QUERY ===\n{query}\n\n"
        "=== STRICT GROUNDED ANSWER ==="
    )

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction_text}]
        },
        "contents": [{
            "parts": [{"text": user_prompt}]
        }],
        "generationConfig": {
            "temperature": float(temperature),
            "maxOutputTokens": 950
        }
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
            return "⚠️ Gemini API returned an empty response. The document passages may not contain relevant content."
        else:
            err_code = res.status_code
            err_msg = res.text
            err_status = ""
            try:
                err_json = res.json().get("error", {})
                err_msg = err_json.get("message", res.text)
                err_status = err_json.get("status", "")
            except Exception:
                pass

            remedy = ""
            if err_code == 404:
                remedy = f"Model '{model}' is not available. Please switch to 'gemini-3.1-flash-lite' or 'gemini-3.5-flash' in the sidebar."
            elif err_code == 429:
                remedy = "Quota limit reached (Rate Limit Exceeded). Please wait 30-60 seconds before submitting another prompt."
            elif err_code in (401, 403):
                remedy = "API key authorization error. Please verify GEMINI_API_KEY in .streamlit/secrets.toml."
            elif err_code in (500, 503):
                remedy = "Google Gemini service is temporarily experiencing high traffic. Please retry in a few moments."

            out = f"**⚠️ Google Gemini API Error [HTTP {err_code}{f' - {err_status}' if err_status else ''}]:**\n\n> {err_msg}"
            if remedy:
                out += f"\n\n💡 **Suggested Fix:** {remedy}"
            return out
    except requests.exceptions.Timeout:
        return "⚠️ **Gemini API Timeout:** The request took longer than 30 seconds. Try asking a more concise question or switching models in the sidebar."
    except requests.exceptions.ConnectionError:
        return "⚠️ **Network Connection Error:** Could not connect to Google Gemini API servers. Please check your internet connection."
    except Exception as exc:
        return f"⚠️ **Unexpected Error:** {str(exc)}"


def local_extractive_answer(query: str, retrieved_passages: List[Tuple[Dict[str, Any], float]]) -> str:
    """Offline Zero-Key extractive answer synthesizer."""
    words = set(re.findall(r"\w+", query.lower())) - {"what", "is", "the", "how", "why", "are", "in", "of", "and", "to", "a"}
    scored = []

    for chunk, chunk_score in retrieved_passages:
        for s in re.split(r"(?<=[.!?])\s+", chunk["text"]):
            s_clean = s.strip()
            if len(s_clean) > 25:
                w = set(re.findall(r"\w+", s_clean.lower()))
                overlap = len(w.intersection(words))
                if overlap > 0:
                    scored.append((overlap * chunk_score, s_clean, chunk.get("label", f"Page {chunk['page_num']}")))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_sent = scored[:3]

    if not top_sent:
        return "*(Offline Mode)* The retrieved passages do not have high keyword alignment. Please check the source passages below."

    lines = ["*(Generated with Offline Extractive QA — No API Key)*\n"]
    for sc, sent, origin in top_sent:
        lines.append(f"- **[{origin}]** \"{sent}\"")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# 8. Sidebar Controls: Theme Buttons, Protected Key, Health & Hyperparameters
# -----------------------------------------------------------------------------
with st.sidebar:
    # Top Brand Header
    st.markdown("""
    <div class="brand-header">
        <div class="brand-logo">🩸</div>
        <div class="brand-name">Neural<span>RAG</span> Studio</div>
    </div>
    """, unsafe_allow_html=True)

    # 1-Click Theme Switcher Buttons (Light / Dark Switch with Buttons)
    st.markdown("<p style='font-size:0.84rem; font-weight:700; margin-bottom:6px;'>🎨 Theme Mode</p>", unsafe_allow_html=True)
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        if st.button("🌙 Dark", use_container_width=True, type="primary" if is_dark else "secondary", key="theme_btn_dark"):
            st.session_state["theme_mode"] = "dark"
            st.rerun()
    with t_col2:
        if st.button("☀️ Light", use_container_width=True, type="secondary" if is_dark else "primary", key="theme_btn_light"):
            st.session_state["theme_mode"] = "light"
            st.rerun()

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    # Protected Primary API Key Setup
    active_key, key_source = get_primary_api_key()

    # Protected Key Status Card
    if active_key:
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid #10b981; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;">
            <div style="color: #10b981; font-size: 0.82rem; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                <span>🔒</span> Main API Key Protected & Active
            </div>
            <div style="color: {t_text_secondary}; font-size: 0.74rem; margin-top: 3px;">
                Loaded via {key_source.split('(')[0].strip()} · 100% hidden & secured
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: rgba(225, 29, 72, 0.14); border: 1px solid #e11d48; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;">
            <div style="color: #fda4af; font-size: 0.82rem; font-weight: 700;">⚠️ Main API Key Missing</div>
            <div style="color: {t_text_secondary}; font-size: 0.74rem; margin-top: 3px;">
                Configure <code>GEMINI_API_KEY</code> in <code>.streamlit/secrets.toml</code>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # API Health & Error Check Diagnostics Expander
    with st.expander("⚡ API Error & Health Inspector", expanded=False):
        st.caption("Live test your protected API key to diagnose connection errors, quota limits, or model status:")
        diag_model = st.selectbox(
            "Diagnostics Test Model",
            [
                "gemini-3.1-flash-lite",
                "gemini-3.5-flash-lite",
                "gemini-3.5-flash",
                "gemini-3.1-flash-lite-preview",
                "gemini-flash-lite-latest"
            ],
            index=0,
            key="diag_model_select"
        )
        if st.button("🔍 Check API Status & Errors", use_container_width=True):
            with st.spinner("Pinging Google Gemini API..."):
                diag_res = check_gemini_api_health(active_key, model=diag_model)
                st.session_state["api_diag_result"] = diag_res

        if "api_diag_result" in st.session_state:
            d_res = st.session_state["api_diag_result"]
            if d_res["status"] == "success":
                st.success(
                    f"**✅ API Operational & Healthy!**\n\n"
                    f"- **HTTP Status:** `200 OK`\n"
                    f"- **Response Latency:** `{d_res['latency_ms']} ms`\n"
                    f"- **Active Model:** `{d_res['model']}`\n"
                    f"- **Result:** {d_res['message']}"
                )
            else:
                st.error(
                    f"**❌ API Error Detected:**\n\n"
                    f"- **HTTP Code:** `{d_res.get('code', 'Error')}`\n"
                    f"- **Message:** {d_res.get('message', 'Unknown error')}\n\n"
                    f"💡 **Actionable Remedy:** {d_res.get('remedy', 'Check your Google AI Studio credentials.')}"
                )

    # New Chat / Reset Session Button
    if st.button("➕ New Chat Session", use_container_width=True, type="secondary"):
        st.session_state["messages"] = []
        st.rerun()

    st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid rgba(225,29,72,0.2);'>", unsafe_allow_html=True)

    # Document Upload in Sidebar
    st.markdown("**📁 Universal Document Knowledge Base**")
    uploaded_file = st.file_uploader(
        "Upload PDF, Word, Excel, CSV, or Image",
        type=["pdf", "docx", "xlsx", "xls", "csv", "png", "jpg", "jpeg", "webp", "bmp", "txt", "md"],
        help="Upload course material, scanned PDFs, spreadsheets, or images for AI grounding."
    )

    # Model & Index Settings Accordion
    with st.expander("⚙️ Lab Engine & Hyperparameters", expanded=False):
        gemini_model = st.selectbox(
            "Model Architecture",
            [
                "gemini-3.1-flash-lite",
                "gemini-3.5-flash-lite",
                "gemini-3.5-flash",
                "gemini-3.1-flash-lite-preview",
                "gemini-flash-lite-latest"
            ],
            index=0,
            help="High-efficiency Google Gemini models optimized for fast RAG grounding and multimodal OCR."
        )
        embed_method = st.radio(
            "Vector Space",
            ["Dense Neural (MiniLM)", "Sparse TF-IDF (Fast)"],
            index=0
        )
        top_k = st.slider("Top-K Retrieved Chunks", min_value=1, max_value=8, value=4)
        chunk_size = st.slider("Chunk Size (chars)", min_value=200, max_value=1200, value=650, step=50)
        chunk_overlap = st.slider("Chunk Overlap (chars)", min_value=0, max_value=300, value=120, step=20)
        temperature = st.slider("Temperature (0.0 = Strict Factual)", min_value=0.0, max_value=1.0, value=0.0, step=0.05)


# -----------------------------------------------------------------------------
# 9. Document Ingestion Pipeline
# -----------------------------------------------------------------------------
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_id = f"{uploaded_file.name}_{len(file_bytes)}_{chunk_size}_{chunk_overlap}_{embed_method}"

    if st.session_state.get("active_file_id") != file_id:
        with st.spinner("🩸 Parsing document, running OCR & building vector index..."):
            t0 = time.time()
            doc_text, pages, doc_type, aux_data = universal_document_loader(
                uploaded_file,
                api_key=active_key,
                model=gemini_model
            )

            if not doc_text.strip():
                st.error("⚠️ No readable content found in this document.")
                st.stop()

            chunks = build_chunks(pages, chunk_size=chunk_size, overlap=chunk_overlap)
            index_payload = index_chunks(chunks, method=embed_method)
            t_elapsed = time.time() - t0

            st.session_state["active_file_id"] = file_id
            st.session_state["filename"] = uploaded_file.name
            st.session_state["doc_type"] = doc_type
            st.session_state["doc_text"] = doc_text
            st.session_state["pages"] = pages
            st.session_state["chunks"] = chunks
            st.session_state["index_payload"] = index_payload
            st.session_state["indexing_time"] = t_elapsed
            st.session_state["aux_data"] = aux_data


# -----------------------------------------------------------------------------
# 10. Main Dashboard Interface & Multi-Tab Navigation
# -----------------------------------------------------------------------------
chunks = st.session_state.get("chunks", [])
filename = st.session_state.get("filename", "")
doc_type = st.session_state.get("doc_type", "")
index_payload = st.session_state.get("index_payload", None)
aux_data = st.session_state.get("aux_data", {})

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Main App Navigation Tabs
tab_chat, tab_preview, tab_chunks, tab_analytics, tab_guide, tab_downloads = st.tabs([
    "💬 ChatGPT Assistant",
    "👁️ Document & OCR Inspector",
    "🔬 Chunk Inspector",
    "📊 Retrieval Analytics",
    "🎓 Lab Architecture",
    "📥 Downloads"
])

# -----------------------------------------------------------------------------
# TAB 1: ChatGPT-Style Conversational Interface
# -----------------------------------------------------------------------------
with tab_chat:
    # Document Status Bar
    if chunks:
        words = len(st.session_state.get("doc_text", "").split())
        idx_name = "Dense MiniLM" if index_payload[0] == "dense" else "Sparse TF-IDF"
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: space-between; background: {t_bg_card}; border: 1px solid {t_border_card}; border-radius: 10px; padding: 12px 20px; margin-bottom: 20px; box-shadow: {t_card_shadow};">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.3rem;">📄</span>
                <div>
                    <span style="font-weight: 700; color: {t_text_primary};">{filename}</span>
                    <span style="font-size: 0.8rem; color: {t_text_secondary}; margin-left: 8px;">({doc_type})</span>
                </div>
            </div>
            <div style="display: flex; gap: 8px;">
                <span class="metric-pill">🧩 {len(chunks)} Chunks</span>
                <span class="metric-pill">📖 {words:,} Words</span>
                <span class="metric-pill">⚡ {idx_name}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: {t_accent_glow}; border: 1px dashed {t_accent}; border-radius: 10px; padding: 14px 20px; margin-bottom: 20px; text-align: center; color: {t_text_primary}; font-size: 0.92rem;">
            💡 <b>Step 1:</b> Upload a PDF (text/scanned), Word, Excel, CSV, or Image in the sidebar to enable grounded multimodal chat.
        </div>
        """, unsafe_allow_html=True)

    # Empty State with ChatGPT Prompt Suggestions
    if not st.session_state["messages"]:
        st.markdown(f"""
        <div class="welcome-container">
            <div class="welcome-logo">🩸</div>
            <div class="welcome-title">What can I help you discover?</div>
            <div class="welcome-sub">Ask any question grounded in your uploaded documents. Powered by Google {gemini_model}.</div>
        </div>
        """, unsafe_allow_html=True)

        # 4 Prompt Suggestions
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            if st.button("📌 Summarize the core topic & conclusions", use_container_width=True):
                st.session_state["quick_prompt"] = "Provide a comprehensive summary of the core topic, conclusions, and objectives."
            if st.button("🔬 What methodology or algorithm is used?", use_container_width=True):
                st.session_state["quick_prompt"] = "What methodology, algorithms, datasets, or techniques are described?"
        with p_col2:
            if st.button("📊 Extract key statistics & quantitative data", use_container_width=True):
                st.session_state["quick_prompt"] = "Extract all key statistics, figures, results, tables, and quantitative data."
            if st.button("❓ What are the limitations or key findings?", use_container_width=True):
                st.session_state["quick_prompt"] = "What limitations, challenges, or key findings are highlighted?"

    # Render Conversation History with Native Chat Messages for Perfect Markdown Formatting
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🩸"):
                st.markdown(msg["content"])

                # Grounded Evidence Citations
                if msg.get("sources"):
                    with st.expander("📚 Grounded Evidence Passages", expanded=False):
                        for i, (ch, sc) in enumerate(msg["sources"], start=1):
                            pct = max(0.0, min(100.0, sc * 100))
                            source_label = ch.get("label") or f"Source {ch.get('page_num', 1)}"
                            snippet = ch["text"][:360]
                            st.markdown(f"""
                            <div class="citation-card">
                                <div style="display: flex; justify-content: space-between; color: {t_accent}; font-size: 0.8rem; font-weight: 700; margin-bottom: 4px;">
                                    <span>Passage #{i} · {source_label}</span>
                                    <span style="color: #ffffff; background: {t_accent}; padding: 2px 7px; border-radius: 4px;">{pct:.1f}% Match</span>
                                </div>
                                {snippet}...
                            </div>
                            """, unsafe_allow_html=True)

                # Latency & Model Metadata
                latency_val = msg.get('latency', 0.0)
                model_val = msg.get('model', 'Gemini')
                st.caption(f"⚡ Latency: **{latency_val:.2f}s** | 🤖 Model: **{model_val}**")

    # Chat Input Trigger
    user_query = st.chat_input("Ask anything about your uploaded document...")

    if st.session_state.get("quick_prompt"):
        user_query = st.session_state.pop("quick_prompt")

    if user_query and user_query.strip():
        # Append User Message
        st.session_state["messages"].append({"role": "user", "content": user_query})

        with st.spinner("🩸 Thinking & retrieving grounded passages..."):
            t_start = time.time()
            retrieved = []
            final_resp = ""

            if chunks and index_payload is not None:
                retrieved = perform_retrieval(user_query, chunks, index_payload, top_k=top_k)
                context_blocks = []
                for i, (c, s) in enumerate(retrieved, start=1):
                    c_label = c.get("label") or f"Page {c.get('page_num', 1)}"
                    context_blocks.append(f"[Passage {i} | {c_label} | Sim: {s:.3f}]:\n{c['text']}")
                context_str = "\n\n".join(context_blocks)

                if active_key:
                    final_resp = call_gemini_llm(user_query, context_str, active_key, model=gemini_model, temperature=temperature)
                else:
                    final_resp = local_extractive_answer(user_query, retrieved)
            else:
                final_resp = "⚠️ Please upload a document in the left sidebar first so I can ground my answers in your material."

            t_elapsed = time.time() - t_start

            # Append Assistant Message
            st.session_state["messages"].append({
                "role": "assistant",
                "content": final_resp,
                "sources": retrieved,
                "latency": t_elapsed,
                "model": gemini_model if active_key else "Offline Synthesizer"
            })
            st.rerun()


# -----------------------------------------------------------------------------
# TAB 2: Document & Multimodal OCR Inspector
# -----------------------------------------------------------------------------
with tab_preview:
    if chunks:
        st.markdown(f"#### 👁️ Content & OCR Extraction from `{filename}`")
        st.caption(f"Format: **{doc_type}** | Total Chunks: **{len(chunks)}**")
        doc_full = st.session_state.get("doc_text", "")

        # Specialized view for Images
        if "Image" in doc_type and uploaded_file is not None:
            img_c1, img_c2 = st.columns([1, 1])
            with img_c1:
                st.markdown("**Original Image Upload:**")
                st.image(uploaded_file, caption=filename, use_container_width=True)
            with img_c2:
                st.markdown("**Multimodal Vision OCR Transcript:**")
                st.text_area("OCR Result", value=doc_full, height=450)

        # Specialized view for Excel/CSV Spreadsheets
        elif "Spreadsheet" in doc_type and "dfs" in aux_data:
            dfs = aux_data["dfs"]
            st.markdown("**📊 Interactive Spreadsheet Viewer:**")
            sheet_names = list(dfs.keys())
            selected_sheet = st.selectbox("Select Sheet to View:", sheet_names, index=0)
            if selected_sheet in dfs:
                st.dataframe(dfs[selected_sheet], use_container_width=True, height=280)

            st.markdown("**Structured Tabular RAG Chunks Preview:**")
            st.text_area("Parsed Tabular Content", value=doc_full[:16000], height=320)

        # View for PDF & Word
        else:
            st.markdown("**Parsed & OCR-Enhanced Document Content:**")
            st.text_area("Document Content", value=doc_full[:18000], height=480)
    else:
        st.info("Upload a document in the sidebar to inspect its parsed content and OCR output.")


# -----------------------------------------------------------------------------
# TAB 3: Chunk Boundary & Window Inspector
# -----------------------------------------------------------------------------
with tab_chunks:
    if chunks:
        st.markdown("#### 🔬 Chunk Boundary & Sliding Window Inspector")
        st.caption("Inspect exact character spans and overlap windows between adjacent chunks.")

        chunk_search = st.text_input("Filter chunks by keyword:", placeholder="e.g., introduction, dataset, conclusion, sales")
        filtered = [c for c in chunks if chunk_search.lower() in c["text"].lower()] if chunk_search else chunks

        st.caption(f"Showing **{len(filtered)}** of **{len(chunks)}** total chunks.")
        for c in filtered[:15]:
            c_label = c.get("label") or f"Source {c.get('page_num', 1)}"
            with st.expander(f"Chunk #{c['chunk_id']} | {c_label} | Span [{c['start_char']} - {c['end_char']}]"):
                st.code(c["text"], language=None)
    else:
        st.info("Upload a document in the sidebar to inspect vector chunks.")


# -----------------------------------------------------------------------------
# TAB 4: Retrieval Analytics
# -----------------------------------------------------------------------------
with tab_analytics:
    if chunks:
        st.markdown("#### 📊 Vector Similarity Scoring Distribution")
        st.caption("Visualizes Cosine Similarity scores across chunks for a test query.")

        test_q = st.text_input("Test query:", value="main objectives and conclusions", key="tab4_test_q")
        if test_q:
            ranked = perform_retrieval(test_q, chunks, index_payload, top_k=min(12, len(chunks)))
            chart_dict = {}
            for c, s in ranked:
                c_label = c.get("label") or f"P.{c.get('page_num', 1)}"
                chart_dict[f"Chunk #{c['chunk_id']} ({c_label})"] = round(s, 3)
            st.bar_chart(chart_dict)
    else:
        st.info("Upload a document in the sidebar to view similarity analytics.")


# -----------------------------------------------------------------------------
# TAB 5: Architecture & Lab Teaching Guide
# -----------------------------------------------------------------------------
with tab_guide:
    st.markdown("#### 🎓 Interactive Multimodal RAG System Architecture")
    st.markdown("""
    ```
    +-----------------------------------------------------------------------------------------+
    |                    TOP-NOTCH MULTIMODAL NEURAL RAG ARCHITECTURE                         |
    +-----------------------------------------------------------------------------------------+
    
    [ 1. Universal Ingest ]  PDF (Digital + OCR) / Word (.docx) / Excel / CSV / Images
                                                │
                                                ▼
    [ 2. Multimodal OCR ]    Gemini Vision Engine -> Transcribes scans, charts & data tables
                                                │
                                                ▼
    [ 3. Chunking Engine ]   Sliding Window Chunking (Size: 650 chars, Overlap: 120 chars)
                                                │
                                                ▼
    [ 4. Vector Embeddings ] Dense Neural Vectors (MiniLM) or Sparse TF-IDF Index
                                                │
                                                ▼
    [ 5. User Query ]        Query Vectorization -> Cosine Similarity Dot Product Ranking
                                                │
                                                ▼
    [ 6. Top-K Retrieval ]   Extract Top-4 Most Relevant Chunks + Source Citations
                                                │
                                                ▼
    [ 7. Prompt Augment ]    Prompt: "Answer ONLY using these passages:" + Context + Query
                                                │
                                                ▼
    [ 8. Gemini Generation ] Google Gemini 3.1 Flash Lite -> Grounded Factual Answer
    ```
    """)
    st.markdown("""
    **Core AI Concepts for Classroom Discussion:**
    - **Why Multimodal OCR in RAG?** Real-world documents (lecture notes, textbooks, reports) contain scanned text, charts, diagrams, and financial tables that raw PDF extractors completely miss. Multimodal OCR converts visual assets into searchable semantic vectors.
    - **Why Tabular Context Preservation?** When chunking spreadsheets, repeating column headers on every row slice ensures embeddings retain the relationship between columns and values.
    - **Dense vs Sparse:** Dense neural vectors capture synonyms (e.g. *revenue* matches *earnings*); Sparse TF-IDF relies on exact keyword matching.
    """)


# -----------------------------------------------------------------------------
# TAB 6: Download Classroom Repository Files
# -----------------------------------------------------------------------------
with tab_downloads:
    st.markdown("#### 📥 Download Complete Lab Repository")
    st.caption("Clean downloadable files ready for GitHub submission or student handouts:")

    d1, d2 = st.columns(2)

    try:
        with open("app.py", "r", encoding="utf-8") as f:
            app_code = f.read()
    except Exception:
        app_code = "# app.py"

    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            req_code = f.read()
    except Exception:
        req_code = "streamlit\npypdf\npython-docx\nopenpyxl\npandas\nPillow\nsentence-transformers\nscikit-learn\nnumpy\nrequests"

    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme_code = f.read()
    except Exception:
        readme_code = "# README"

    try:
        with open("Student_Lab_Assignment.md", "r", encoding="utf-8") as f:
            assign_code = f.read()
    except Exception:
        assign_code = "# Student Lab Assignment"

    with d1:
        st.download_button("📄 Download `app.py`", data=app_code, file_name="app.py", mime="text/x-python", use_container_width=True)
        st.download_button("📦 Download `requirements.txt`", data=req_code, file_name="requirements.txt", mime="text/plain", use_container_width=True)
    with d2:
        st.download_button("📘 Download `README.md` (GitHub Guide)", data=readme_code, file_name="README.md", mime="text/markdown", use_container_width=True)
        st.download_button("🎓 Download `Student_Lab_Assignment.md`", data=assign_code, file_name="Student_Lab_Assignment.md", mime="text/markdown", use_container_width=True)
