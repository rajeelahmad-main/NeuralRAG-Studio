# 🩸 NeuralRAG Studio: Multimodal RAG with Google Gemini 3.1 Flash Lite

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-e11d48.svg)](https://www.python.org/)
[![Theme: Crimson & Black](https://img.shields.io/badge/Theme-Crimson%20%26%20Black%20%26%20White-dc2626.svg)]()
[![Free Tier](https://img.shields.io/badge/Cost-100%25%20Free%20%26%20Zero%20Paid%20Resources-brightgreen.svg)]()

A modern, high-contrast **Crimson, Black & White** AI laboratory built for Artificial Intelligence, Data Science, and NLP courses.

Features universal multi-format document reading (**PDF, Word `.docx`, Excel `.xlsx`/`.csv`, Images with AI Vision OCR**), powered by **Google Gemini 3.1 Flash Lite** as the dedicated primary LLM, paired with local semantic vector search.

---

## 📑 Table of Contents
1. [Core AI Concept: What is RAG?](#-core-ai-concept-what-is-rag)
2. [Universal Multimodal Document Support](#-universal-multimodal-document-support)
3. [Repository File Structure](#-repository-file-structure)
4. [Security: Protecting Your API Key on GitHub](#-security-protecting-your-api-key-on-github)
5. [Step 1: Uploading Files to GitHub](#-step-1-uploading-files-to-github)
6. [Step 2: Deploying to Streamlit Community Cloud (Free)](#-step-2-deploying-to-streamlit-community-cloud-free)
7. [Running Locally](#-running-locally)
8. [Classroom Exercises & Student Lab Assignment](#-classroom-exercises--student-lab-assignment)

---

## 💡 Core AI Concept: What is RAG?

In modern Artificial Intelligence:
- **Parametric Memory:** Knowledge compressed into the neural weights during pre-training. Prone to hallucinations and stale facts.
- **Non-Parametric Memory:** External documents parsed into chunks, indexed in vector space, and retrieved dynamically.

> **Teaching Note for Students:**  
> RAG **does not fine-tune or train model weights**. The language model remains frozen. Passages are retrieved via **Cosine Similarity** and injected into the **Prompt Context** at inference time.

```
+-----------------------------------------------------------------------------------------+
|                                    RAG PIPELINE FLOW                                    |
+-----------------------------------------------------------------------------------------+
[ Upload File: PDF / Word / Excel / Image ] ──► [ Multimodal Parser / Gemini Vision OCR ]
                                                              │
                                                              ▼
[ Cosine Similarity Top-K ] ◄── [ Query Vector ] ◄── [ Sliding Window Chunks (600c / 100c) ]
            │                                                 │
            ▼                                                 ▼
[ Grounded Context Passages ] ──► [ Prompt Augmentation ] ──► [ Dense MiniLM / Sparse TF-IDF ]
                                            │
                                            ▼
                           [ Google Gemini 3.1 Flash Lite ] ──► Grounded Factual Answer
```

---

## 📂 Universal Multimodal Document Support

| File Type | Extensions | Parsing Technique |
|---|---|---|
| 📄 **PDF Documents** | `.pdf` | Digital text extraction with automated **Gemini Multimodal OCR** for scanned pages & embedded charts |
| 📝 **Word Documents** | `.docx` | `python-docx` extracting headings, bullet points, Markdown tables & embedded figures |
| 📊 **Spreadsheets** | `.xlsx`, `.xls`, `.csv` | Multi-sheet tabular RAG with repeated column headers on every chunk & interactive DataFrame viewer |
| 🖼️ **Images & Scans** | `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp` | **Gemini AI Vision OCR** transcribing text, tables, diagrams, flowcharts & metrics |
| 📃 **Plain Text** | `.txt`, `.md` | Fast UTF-8 text parser with semantic chunking |

---

## 📁 Repository File Structure

```
pdf-rag-lab/
│
├── app.py                     # Main Streamlit Crimson Dashboard & RAG logic
├── requirements.txt           # Python dependencies
├── README.md                  # Complete deployment & student guide
├── Student_Lab_Assignment.md  # Ready-to-use printable student lab worksheet
├── .gitignore                 # Excludes secrets, venvs, and cache from GitHub
└── .streamlit/
    ├── config.toml            # Crimson, Black & White visual theme configuration
    └── secrets.toml           # Local API key storage (Protected by .gitignore)
```

---

## 🔒 Security: Protecting Your API Key on GitHub & Live Deployments

### 1. Protection Against GitHub Leaks
- The [`.gitignore`](file:///c:/Users/amina/Desktop/pdf-rag-lab/.gitignore) file strictly excludes `.streamlit/secrets.toml`, `.env`, and virtual environment folders.
- [`app.py`](file:///c:/Users/amina/Desktop/pdf-rag-lab/app.py) contains **zero hardcoded keys**. All keys are kept private.

### 2. Complete Dashboard API Key Protection
- The dashboard **solely uses your primary API key** configured in `.streamlit/secrets.toml` or the `GEMINI_API_KEY` environment variable.
- **100% Invisible & Protected:** The raw API key string is never rendered, displayed, or exposed anywhere on the dashboard.
- **Live Error Diagnostics:** Includes an interactive **API Error & Health Inspector** tool directly in the sidebar to verify connection status, test model availability, and diagnose API errors (HTTP codes, rate limits, deprecations) in real time.
- **Dual-Theme Color Switch:** Features instant switching between **🌙 Dark Mode** and **☀️ Light Mode** with crisp contrast.

### 3. Strict Zero-Hallucination Grounding
- **Strict Guardrails:** The model is constrained to answer solely from uploaded text passages.
- **Negative Rejection:** If a question cannot be answered from the document, it outputs: *"The uploaded document does not contain information to answer this question."*
- **External Info Isolation:** The model **NEVER** supplies external knowledge unless the user explicitly asks for information beyond the document.

---

## 🚀 Step 1: Uploading Files to GitHub

### Option A: Via GitHub Web Interface
1. Go to [github.com](https://github.com/) and create a **New Repository** named `pdf-rag-lab` (set to **Public**).
2. Click **uploading an existing file**.
3. Drag and drop:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `Student_Lab_Assignment.md`
   - `.gitignore`
   - `.streamlit/config.toml` *(Do NOT upload `secrets.toml`)*
4. Click **Commit changes**.

### Option B: Via Git Command Line
```bash
git init
git add .
git commit -m "NeuralRAG Studio: Crimson Multimodal Edition"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pdf-rag-lab.git
git push -u origin main
```
*(Notice: git will automatically skip `.streamlit/secrets.toml` because of `.gitignore`!)*

---

## 🌐 Step 2: Deploying to Streamlit Community Cloud (Free)

1. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
2. Click **Create app**.
3. Select your repository: `YOUR_USERNAME/pdf-rag-lab`, Branch: `main`, Main file path: `app.py`.
4. Click **Advanced settings** → **Secrets**, and enter your Gemini API key:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key_here"
   ```
5. Click **Deploy!** Your app will be live on the web in 1–2 minutes!

---

## 💻 Running Locally

### Recommended Python Version: `3.10`, `3.11`, or `3.12`

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/pdf-rag-lab.git
cd pdf-rag-lab

# 2. Create virtual environment
python -m venv .venv

# 3. Activate environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Launch the dashboard
streamlit run app.py
```

The app will launch at `http://localhost:8501`.

---

## 🎓 Classroom Exercises & Student Lab Assignment

A complete student lab worksheet is provided in [`Student_Lab_Assignment.md`](file:///c:/Users/amina/Desktop/pdf-rag-lab/Student_Lab_Assignment.md).

### Suggested 90-Minute Lab Plan:
1. **00–15 min: Concept Introduction:** Parametric vs. Non-Parametric memory and RAG architecture.
2. **15–30 min: Multimodal Ingestion:** Students upload different file formats (PDF, Word, Excel, or an Image with OCR) and inspect parsed text.
3. **30–50 min: Grounded Q&A & Hallucination Testing:** Students run grounded queries vs unanswerable queries.
4. **50–70 min: Dense vs. Sparse Experiment:** Students compare MiniLM dense semantic vectors against TF-IDF keyword vectors.
5. **70–90 min: Hyperparameter Study:** Students vary Chunk Size and Top-K, recording results in the worksheet.

---

## 📜 License
This project is open-source under the MIT License. Feel free to use and adapt for university courses and labs.
