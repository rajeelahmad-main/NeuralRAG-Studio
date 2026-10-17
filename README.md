# NeuralRAG Studio v2.0 — AI Document Intelligence Platform

**CRISP + Multi-File Hybrid RAG + Corrective RAG (CRAG) + Gemini Model Selector**

NeuralRAG is a full-stack, commercial-grade AI document chat platform inspired by ChatGPT's conversational workspace. It combines multi-format document ingestion, hybrid vector + keyword retrieval, **Corrective RAG (CRAG)** self-healing search, interactive `[Source N]` citations, and a live server-managed **Gemini Model Selector**.

---

## 1. Architecture Summary

| Layer | Technology Stack | Key Responsibilities |
| :--- | :--- | :--- |
| **Frontend (`frontend/`)** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide Icons, `react-markdown` + `remark-gfm` | ChatGPT-inspired 3-column layout, collapsible sidebar, date-grouped history, GPT-style Gemini model dropdown, multiline auto-resizing composer, SSE streaming with `AbortController` Stop Generation, Light/Dark themes, and slide-over Citation & Document Inspector. |
| **Backend (`backend/`)** | Python 3.10+, FastAPI, Uvicorn, Pydantic v2, SSE Streaming | REST + Server-Sent Events (`/api/conversations/{id}/stream`), server-side API key isolation, sliding-window rate limiting, and input sanitization. |
| **RAG & CRAG Engine (`backend/rag_engine.py`, `backend/vector_store.py`)** | Hybrid Vector Index (Word N-gram TF-IDF + Subword Semantic Vectors + Optional MiniLM Dense Embeddings + Cross-Feature Reranker) | 3 distinct retrieval modes (`corrective_rag`, `document_search`, `compare_documents`), relevance grading (`relevant` / `ambiguous` / `irrelevant`), automatic query expansion & bounded retry loop, deduplication, abstention on missing evidence, and `<untrusted_document_evidence>` prompt-injection sandboxing. |
| **Persistence (`backend/database.py`, `storage/`)** | SQLite (`storage/neuralrag.db`), Persistent Pickle Vector Indexes (`storage/indexes/`), Sanitized File Vault (`storage/uploads/`) | Persistent collections, documents, provenance-rich chunks, conversations, messages, and user settings. |

---

## 2. Supported Document Formats & Provenance Metadata

- **PDF (`.pdf`)**: Page-by-page extraction with automatic Gemini Vision OCR fallback for scanned pages (`Page N` provenance).
- **Word (`.docx`)**: Section heading tracking + automatic conversion of embedded Word tables into structured Markdown grids.
- **Excel & CSV (`.xlsx`, `.csv`)**: Multi-sheet ingestion with quantitative column summary statistics (`min`, `max`, `mean`, `sum`) and row-range (`Sheet • Rows X-Y`) provenance.
- **Markdown & Text (`.md`, `.txt`)**: Heading-aware semantic chunking with character offset tracking.
- **Images (`.png`, `.jpg`, `.jpeg`, `.webp`)**: Gemini Vision OCR & visual layout extraction.

---

## 3. Environment Variables & API Key Security

Copy [`.env.example`](file:///.env.example) to `.env` (or configure `.streamlit/secrets.toml`):

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
DEFAULT_GEMINI_MODEL=gemini-3.1-flash-lite
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

> **Security Guarantee:** `GEMINI_API_KEY` is read strictly on the FastAPI server (`backend/config.py`) and is **never** sent to the browser, exposed in `NEXT_PUBLIC_*` variables, or returned in any API payload.

---

## 4. Exact Installation & Startup Instructions

### Quick Start (Windows One-Click Launcher)
Double-click or run [`start_platform.bat`](file:///start_platform.bat) to start both the FastAPI backend (`:8000`) and Next.js frontend (`:3000`).

### Manual Setup & Startup

#### Step 1: Install Backend Python Dependencies
```bash
py -3.10 -m pip install -r requirements.txt
```

#### Step 2: Start the FastAPI Backend Server (Port 8000)
```bash
py -3.10 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Step 3: Install & Start the Next.js Frontend (Port 3000)
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 5. Automated Testing & Verification

Run the automated backend test suite covering API key isolation, model registry discovery, multi-file ingestion (`MD`, `CSV`, `XLSX`, `DOCX`), path traversal protection, Hybrid RAG, Corrective RAG (CRAG), Compare Documents mode, citation chunk inspection, SSE streaming, message edit/resubmit, and abstention:

```bash
py -3.10 -m pytest backend/tests/test_backend.py -v
```

Verify the production Next.js TypeScript & Tailwind build:

```bash
cd frontend
npm run build
```
