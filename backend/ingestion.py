"""
Multi-Format Document Ingestion & Semantic Chunking Service.
Supports PDF (digital + Vision OCR), DOCX, TXT, Markdown, CSV, XLSX, and Images.
Implements strict path-traversal protection, size limits, and rich source metadata extraction.
"""

import base64
from io import BytesIO
from pathlib import Path
import re
import uuid
from typing import Any, Dict, List, Tuple

import numpy as np
import pypdf
import requests

from backend.config import (
    ALLOWED_EXTENSIONS,
    DEFAULT_GEMINI_MODEL,
    MAX_UPLOAD_SIZE_BYTES,
    UPLOADS_DIR,
    get_server_gemini_api_key,
)

try:
    import docx
except ImportError:
    docx = None

try:
    import pandas as pd
except ImportError:
    pd = None


def sanitize_filename(filename: str) -> str:
    """
    Strictly prevents path traversal attacks (e.g. ../../etc/passwd or ..\\Windows).
    Strips directory components and unsafe characters.
    """
    if not filename:
        return "document.txt"
    # Extract only the final basename across both POSIX and Windows separators
    raw_name = filename.replace("\\", "/").split("/")[-1]
    clean = re.sub(r"[^a-zA-Z0-9._\- ()]", "_", raw_name).strip(" .")
    if not clean or ".." in clean:
        clean = f"file_{uuid.uuid4().hex[:8]}.txt"
    return clean


def validate_upload_file(filename: str, file_size: int) -> Tuple[bool, str, str]:
    """Validates file extension, path safety, and byte size."""
    safe_name = sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, safe_name, f"Unsupported file format '{ext}'. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if file_size <= 0:
        return False, safe_name, "Uploaded file is empty (0 bytes)."
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        return False, safe_name, f"File exceeds maximum allowed size of {max_mb} MB."
    return True, safe_name, "OK"


def save_uploaded_bytes_safely(collection_id: str, doc_id: str, safe_name: str, file_bytes: bytes) -> Path:
    """Saves uploaded bytes inside a collection-scoped folder strictly within UPLOADS_DIR."""
    safe_col = re.sub(r"[^a-zA-Z0-9_\-]", "", collection_id) or "default"
    target_dir = (UPLOADS_DIR / safe_col).resolve()
    uploads_root = UPLOADS_DIR.resolve()
    if not str(target_dir).startswith(str(uploads_root)):
        raise ValueError("Invalid collection directory path traversal attempt blocked.")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = (target_dir / f"{doc_id}_{safe_name}").resolve()
    if not str(target_path).startswith(str(uploads_root)):
        raise ValueError("Invalid file path traversal attempt blocked.")
    target_path.write_bytes(file_bytes)
    return target_path


def perform_vision_ocr(image_bytes: bytes, mime_type: str = "image/png", model: str = DEFAULT_GEMINI_MODEL) -> str:
    """Transcribes scanned PDF pages or standalone images using server-side Gemini Vision."""
    api_key, _ = get_server_gemini_api_key()
    if not api_key:
        return "[Visual/Scanned Content — Configure server GEMINI_API_KEY for OCR]"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "You are a precision Document & Vision OCR Engine.\n"
        "Transcribe all visible text, headings, tables (as Markdown tables), numbers, and chart labels verbatim.\n"
        "Do not summarize or invent content."
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": mime_type, "data": b64_data}}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1800}
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            candidates = res.json().get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                return "".join(p.get("text", "") for p in parts if "text" in p).strip()
        return f"[OCR status {res.status_code}]"
    except Exception as exc:
        return f"[OCR error: {str(exc)}]"


def _detect_heading_in_text(text: str) -> str:
    """Extracts the first prominent heading or title line from a block of text."""
    for line in text.splitlines()[:6]:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            return s.lstrip("#").strip()[:90]
        if 3 < len(s) < 80 and (s.isupper() or s.istitle()) and not s.endswith("."):
            return s[:90]
    return ""


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


def parse_pdf_bytes(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    reader = pypdf.PdfReader(BytesIO(file_bytes))
    sections: List[Dict[str, Any]] = []
    ocr_pages = 0

    for i, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
        except Exception:
            raw_text = ""

        cleaned = sanitize_extracted_text(raw_text)
        if len(cleaned) < 40 and hasattr(page, "images") and len(page.images) > 0:
            try:
                first_img = page.images[0]
                ocr_txt = perform_vision_ocr(first_img.data, "image/png")
                if ocr_txt and not ocr_txt.startswith("[OCR"):
                    cleaned = sanitize_extracted_text(ocr_txt)
                    ocr_pages += 1
            except Exception:
                pass

        if cleaned:
            heading = _detect_heading_in_text(cleaned)
            sections.append({
                "page_number": i,
                "heading": heading,
                "sheet_name": "",
                "row_range": "",
                "text": cleaned
            })

    meta = {"total_pages": len(reader.pages), "ocr_pages": ocr_pages, "format": "PDF"}
    return sections, meta


def parse_docx_bytes(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if docx is None:
        raise RuntimeError("python-docx is not installed.")

    doc = docx.Document(BytesIO(file_bytes))
    sections: List[Dict[str, Any]] = []
    current_lines: List[str] = []
    current_heading = "Document Overview"
    sec_num = 1

    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue
        style_name = (p.style.name or "").lower() if p.style else ""
        if "heading" in style_name or "title" in style_name:
            if current_lines:
                sections.append({
                    "page_number": sec_num,
                    "heading": current_heading,
                    "sheet_name": "",
                    "row_range": "",
                    "text": "\n".join(current_lines)
                })
                sec_num += 1
                current_lines = []
            current_heading = txt[:100]
            current_lines.append(f"### {txt}")
        else:
            current_lines.append(txt)
            if sum(len(x) for x in current_lines) > 1200:
                sections.append({
                    "page_number": sec_num,
                    "heading": current_heading,
                    "sheet_name": "",
                    "row_range": "",
                    "text": "\n".join(current_lines)
                })
                sec_num += 1
                current_lines = []

    for t_idx, table in enumerate(doc.tables, start=1):
        if not table.rows:
            continue
        headers = [c.text.strip().replace("\n", " ") for c in table.rows[0].cells]
        md_lines = [
            f"#### Table {t_idx}",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |"
        ]
        for row in table.rows[1:]:
            vals = [c.text.strip().replace("\n", " ") for c in row.cells]
            md_lines.append("| " + " | ".join(vals) + " |")
        current_lines.append("\n".join(md_lines))

    if current_lines:
        sections.append({
            "page_number": sec_num,
            "heading": current_heading,
            "sheet_name": "",
            "row_range": "",
            "text": "\n".join(current_lines)
        })

    meta = {"total_pages": len(sections), "tables_count": len(doc.tables), "format": "DOCX"}
    return sections, meta


def _df_to_markdown(df: Any, max_rows: int = 30) -> str:
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, r in df.head(max_rows).iterrows():
        vals = [str(v).replace("\n", " ").strip() for v in r.values]
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + rows)


def parse_spreadsheet_bytes(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if pd is None:
        raise RuntimeError("pandas is not installed.")

    lower = filename.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(BytesIO(file_bytes))
        sheets = {"CSV_Sheet": df}
    else:
        sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None)

    sections: List[Dict[str, Any]] = []
    sec_num = 1
    step = 25

    for sheet_name, df_sheet in sheets.items():
        df_clean = df_sheet.dropna(how="all")
        total_rows, total_cols = df_clean.shape
        cols = [str(c) for c in df_clean.columns]

        # Compute summary stats for numeric columns
        num_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        stats_lines = []
        for nc in num_cols[:6]:
            s_mean = df_clean[nc].mean()
            s_sum = df_clean[nc].sum()
            s_min = df_clean[nc].min()
            s_max = df_clean[nc].max()
            stats_lines.append(f"- {nc}: Sum={s_sum:.2f}, Mean={s_mean:.2f}, Min={s_min:.2f}, Max={s_max:.2f}")

        summary_block = (
            f"### Sheet: {sheet_name} ({total_rows} rows, {total_cols} columns)\n"
            f"Columns: {', '.join(cols)}\n"
        )
        if stats_lines:
            summary_block += "Summary Statistics:\n" + "\n".join(stats_lines) + "\n"

        if total_rows == 0:
            sections.append({
                "page_number": sec_num,
                "heading": f"Sheet: {sheet_name}",
                "sheet_name": str(sheet_name),
                "row_range": "Empty",
                "text": summary_block + "(Empty sheet)"
            })
            sec_num += 1
        else:
            for start_idx in range(0, total_rows, step):
                end_idx = min(start_idx + step, total_rows)
                row_range_label = f"Rows {start_idx + 1}-{end_idx}"
                df_slice = df_clean.iloc[start_idx:end_idx]
                md_table = _df_to_markdown(df_slice, max_rows=step)
                text_block = f"{summary_block}\n#### Data ({row_range_label}):\n{md_table}"
                sections.append({
                    "page_number": sec_num,
                    "heading": f"Sheet {sheet_name} ({row_range_label})",
                    "sheet_name": str(sheet_name),
                    "row_range": row_range_label,
                    "text": text_block
                })
                sec_num += 1

    meta = {"total_pages": len(sections), "sheets": list(sheets.keys()), "format": "SPREADSHEET"}
    return sections, meta


def parse_text_or_markdown_bytes(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    raw_text = file_bytes.decode("utf-8", errors="ignore").strip()
    if not raw_text:
        return [], {"total_pages": 0, "format": "TEXT"}

    # Split by markdown headings if present, otherwise by paragraph groups
    blocks = re.split(r"(?m)^(?=#{1,3}\s+)", raw_text)
    sections: List[Dict[str, Any]] = []
    sec_num = 1

    for blk in blocks:
        blk_s = blk.strip()
        if not blk_s:
            continue
        heading = _detect_heading_in_text(blk_s) or f"Section {sec_num}"
        sections.append({
            "page_number": sec_num,
            "heading": heading,
            "sheet_name": "",
            "row_range": "",
            "text": blk_s
        })
        sec_num += 1

    return sections, {"total_pages": len(sections), "format": "MARKDOWN/TEXT"}


def parse_image_bytes(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    ext = Path(filename).suffix.lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else ("image/webp" if ext == ".webp" else "image/png")
    ocr_text = perform_vision_ocr(file_bytes, mime_type=mime)
    sections = [{
        "page_number": 1,
        "heading": f"Image OCR: {filename}",
        "sheet_name": "",
        "row_range": "",
        "text": ocr_text
    }]
    return sections, {"total_pages": 1, "format": "IMAGE_OCR"}


def build_document_chunks(
    document_id: str,
    filename: str,
    sections: List[Dict[str, Any]],
    chunk_size: int = 700,
    chunk_overlap: int = 120
) -> List[Dict[str, Any]]:
    """
    Slices parsed document sections into overlapping chunks while preserving exact
    provenance metadata (filename, page_number, heading, sheet_name, row_range, char_start/end).
    """
    chunks: List[Dict[str, Any]] = []
    chunk_idx = 1

    for sec in sections:
        text = sec.get("text", "").strip()
        if not text:
            continue

        page_num = sec.get("page_number", 1)
        heading = sec.get("heading", "")
        sheet_name = sec.get("sheet_name", "")
        row_range = sec.get("row_range", "")

        # If it's a spreadsheet block, keep the table slice intact if reasonable
        if sheet_name and len(text) <= chunk_size * 2:
            chunks.append({
                "id": f"chk_{document_id}_{chunk_idx}",
                "document_id": document_id,
                "chunk_index": chunk_idx,
                "text": text,
                "filename": filename,
                "page_number": page_num,
                "heading": heading,
                "sheet_name": sheet_name,
                "row_range": row_range,
                "char_start": 0,
                "char_end": len(text),
                "metadata": {
                    "location_label": f"{sheet_name} · {row_range}" if row_range else f"Sheet: {sheet_name}"
                }
            })
            chunk_idx += 1
            continue

        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            # Prefer breaking at a newline or sentence boundary if not at end of text
            if end < text_len:
                window = text[start:end]
                last_break = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("\n"))
                if last_break > chunk_size // 2:
                    end = start + last_break + 1

            slice_text = text[start:end].strip()
            if slice_text:
                loc_parts = [f"Page {page_num}"]
                if heading:
                    loc_parts.append(heading)
                if sheet_name:
                    loc_parts.append(f"Sheet: {sheet_name}")
                if row_range:
                    loc_parts.append(row_range)

                chunks.append({
                    "id": f"chk_{document_id}_{chunk_idx}",
                    "document_id": document_id,
                    "chunk_index": chunk_idx,
                    "text": slice_text,
                    "filename": filename,
                    "page_number": page_num,
                    "heading": heading,
                    "sheet_name": sheet_name,
                    "row_range": row_range,
                    "char_start": start,
                    "char_end": end,
                    "metadata": {
                        "location_label": " · ".join(loc_parts)
                    }
                })
                chunk_idx += 1

            if end >= text_len:
                break
            start = max(end - chunk_overlap, start + 1)

    return chunks


def ingest_document_bytes(
    document_id: str,
    filename: str,
    file_bytes: bytes,
    chunk_size: int = 700,
    chunk_overlap: int = 120
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Main entry point to parse any supported file and produce provenance-rich chunks."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        sections, meta = parse_pdf_bytes(file_bytes, filename)
    elif ext == ".docx":
        sections, meta = parse_docx_bytes(file_bytes, filename)
    elif ext in (".xlsx", ".xls", ".csv"):
        sections, meta = parse_spreadsheet_bytes(file_bytes, filename)
    elif ext in (".png", ".jpg", ".jpeg", ".webp"):
        sections, meta = parse_image_bytes(file_bytes, filename)
    else:
        sections, meta = parse_text_or_markdown_bytes(file_bytes, filename)

    chunks = build_document_chunks(
        document_id=document_id,
        filename=filename,
        sections=sections,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return chunks, meta
