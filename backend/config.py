"""
Server-side configuration and secret management for NeuralRAG Platform.
Strictly keeps API keys on the server and never exposes them to clients.
"""

import os
from pathlib import Path
from typing import Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(STORAGE_DIR / "uploads")))
VECTOR_INDEX_DIR = Path(os.getenv("VECTOR_INDEX_DIR", str(STORAGE_DIR / "indexes")))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(STORAGE_DIR / "neuralrag.db")))

# Ensure storage directories exist safely
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_INDEX_DIR.mkdir(parents=True, exist_ok=True)

# Security & Operational Limits
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".webp"}
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))

# RAG & Corrective RAG (CRAG) Parameters
DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-3.1-flash-lite")
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
CRAG_RELEVANCE_THRESHOLD = float(os.getenv("CRAG_RELEVANCE_THRESHOLD", "0.22"))
CRAG_AMBIGUOUS_THRESHOLD = float(os.getenv("CRAG_AMBIGUOUS_THRESHOLD", "0.12"))
CRAG_MAX_RETRIES = int(os.getenv("CRAG_MAX_RETRIES", "2"))
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))


def get_server_gemini_api_key() -> Tuple[str, str]:
    """
    Retrieves the Gemini API key exclusively on the server side.
    Checks:
      1. Environment variable GEMINI_API_KEY
      2. .streamlit/secrets.toml (preserving compatibility with existing setup)
    Returns (api_key, source_label) — the key value itself is NEVER sent to clients.
    """
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key and env_key != "your_gemini_api_key_here":
        return env_key, "Environment Variable"

    secrets_path = BASE_DIR / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import toml
            data = toml.load(str(secrets_path))
            key = str(data.get("GEMINI_API_KEY", "")).strip()
            if key:
                return key, "Server Secrets Store (.streamlit/secrets.toml)"
        except Exception:
            # Fallback line parser if toml module fails
            try:
                for line in secrets_path.read_text(encoding="utf-8").splitlines():
                    line_s = line.strip()
                    if line_s.startswith("GEMINI_API_KEY") and "=" in line_s:
                        val = line_s.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val, "Server Secrets Store (.streamlit/secrets.toml)"
            except Exception:
                pass

    return "", "Not Configured"
