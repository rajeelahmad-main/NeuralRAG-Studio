# ⚡ NeuralRAG Studio — Frontend (Vercel Production)

> **Commercial AI Document Intelligence Platform**  
> Multi-File Ingestion • Corrective RAG (CRAG) • Gemini Model Selector • Clickable Citations • Pure Black Dark Theme

---

## 🌟 Overview

This is the standalone **Next.js 14 + TypeScript + Tailwind CSS** frontend for **NeuralRAG Studio**, designed for 1-click deployment on **Vercel**.

* **ChatGPT-Style Layout**: Left collapsible sidebar, centered landing cards, and bottom composer.
* **Multi-File Workspace**: Supports PDF, DOCX, XLSX, CSV, Markdown, Text, and Scanned Images (Multimodal Gemini Vision OCR).
* **Gemini Model Selector**: Dynamic switching between `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-3.5-flash`, and `gemini-3.1-pro-preview`.
* **Corrective RAG (CRAG)**: Evaluates semantic relevance scores, runs query rewriting when confidence is low, and returns diagnostic traces.
* **Clickable Citations**: Inline `[Source N]` tags that open verified excerpts, document provenance, page numbers, and similarity grades.
* **Dual Theme Engine**: Pure Dark Mode (`#09090b`) and Light Mode with instant toggle.

---

## 🚀 1-Click Deployment to Vercel

1. Go to [vercel.com/new](https://vercel.com/new) and select **`ragfrontend`**.
2. Add your **Environment Variable**:
   * `GEMINI_API_KEY` = `your_gemini_api_key_here`
3. Click **Deploy**.

The platform is 100% self-contained with built-in Next.js serverless route handlers, and will be live in under 60 seconds!

---

## 🔗 Optional Backend Connection

If you are hosting a separate Python FastAPI backend (e.g. on Render or Railway), simply add:
* `BACKEND_URL` = `https://your-fastapi-backend.onrender.com`

When `BACKEND_URL` is omitted, `ragfrontend` runs seamlessly on Vercel's built-in edge API engine.

---

## 💻 Local Development

```bash
# 1. Install dependencies
npm install

# 2. Run local development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.
