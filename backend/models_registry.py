"""
Server-Side Gemini Model Registry & Extensible LLM Provider Architecture.
Discovers, validates, and serves model metadata without ever exposing API keys.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import requests

from backend.config import DEFAULT_GEMINI_MODEL, LLM_TIMEOUT_SECONDS, get_server_gemini_api_key


class BaseLLMProvider(ABC):
    """Extensible provider interface so additional LLM providers can be added seamlessly."""

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def list_models(self, verify_live: bool = False) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def generate(
        self,
        model_id: str,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1200
    ) -> Tuple[bool, str, Dict[str, Any]]:
        pass


# Curated registry of real, supported Gemini models with friendly display names & capabilities
GEMINI_CURATED_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "gemini-3.1-flash-lite",
        "name": "Gemini 3.1 Flash Lite",
        "provider": "Google Gemini",
        "tier": "Flash Lite",
        "description": "Ultra-fast, low-latency model ideal for everyday document chat, CRAG grading, and multimodal OCR.",
        "capabilities": ["Fast Chat", "Document RAG", "CRAG Grading", "Multimodal Vision OCR"],
        "context_window": "1M tokens",
        "is_default": True
    },
    {
        "id": "gemini-3.5-flash-lite",
        "name": "Gemini 3.5 Flash Lite",
        "provider": "Google Gemini",
        "tier": "Flash Lite",
        "description": "High-efficiency next-gen lightweight model for rapid multi-document synthesis and citations.",
        "capabilities": ["Fast Chat", "Multi-Doc Synthesis", "CRAG Grading", "Vision OCR"],
        "context_window": "1M tokens",
        "is_default": False
    },
    {
        "id": "gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "provider": "Google Gemini",
        "tier": "Flash",
        "description": "Balanced reasoning and speed for complex multi-file comparisons, tables, and deep analysis.",
        "capabilities": ["Deep Reasoning", "Compare Documents", "Complex Tables", "Vision OCR"],
        "context_window": "1M tokens",
        "is_default": False
    },
    {
        "id": "gemini-3.1-pro-preview",
        "name": "Gemini 3.1 Pro",
        "provider": "Google Gemini",
        "tier": "Pro",
        "description": "Demanding analytical reasoning, cross-report discrepancy detection, and nuanced synthesis.",
        "capabilities": ["Advanced Reasoning", "Cross-Doc Audit", "Long Context"],
        "context_window": "2M tokens",
        "is_default": False
    },
    {
        "id": "gemini-flash-lite-latest",
        "name": "Gemini Flash Lite (Latest Rolling)",
        "provider": "Google Gemini",
        "tier": "Flash Lite",
        "description": "Rolling alias pointing to Google's latest stable Flash Lite checkpoint.",
        "capabilities": ["Fast Chat", "Document RAG", "Citations"],
        "context_window": "1M tokens",
        "is_default": False
    }
]


class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self):
        self._discovery_cache: Dict[str, Any] = {
            "timestamp": 0.0,
            "available_api_ids": set(),
            "verified_models": {},
            "last_error": None
        }

    def get_provider_name(self) -> str:
        return "Google Gemini"

    def _discover_account_models(self, api_key: str, force: bool = False) -> Tuple[set, Optional[str]]:
        now = time.time()
        if not force and self._discovery_cache["available_api_ids"] and (now - self._discovery_cache["timestamp"] < 300):
            return self._discovery_cache["available_api_ids"], self._discovery_cache["last_error"]

        if not api_key:
            return set(), "Server API key is not configured."

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                models_data = res.json().get("models", [])
                ids = set()
                for m in models_data:
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        raw_name = m.get("name", "")
                        clean_id = raw_name.replace("models/", "")
                        ids.add(clean_id)
                self._discovery_cache["available_api_ids"] = ids
                self._discovery_cache["timestamp"] = now
                self._discovery_cache["last_error"] = None
                return ids, None
            else:
                err_msg = f"HTTP {res.status_code} during model discovery"
                self._discovery_cache["last_error"] = err_msg
                return set(), err_msg
        except Exception as exc:
            err_msg = f"Discovery network error: {str(exc)}"
            self._discovery_cache["last_error"] = err_msg
            return set(), err_msg

    def verify_single_model(self, model_id: str) -> Dict[str, Any]:
        """Actively pings a specific model to verify live generation access and measure latency."""
        api_key, key_source = get_server_gemini_api_key()
        if not api_key:
            return {
                "model_id": model_id,
                "verified": False,
                "status": "unavailable",
                "latency_ms": 0,
                "message": "Server GEMINI_API_KEY is not configured."
            }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        payload = {
            "contents": [{"parts": [{"text": "Reply with OK."}]}],
            "generationConfig": {"maxOutputTokens": 5, "temperature": 0.0}
        }
        t0 = time.time()
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            latency_ms = int((time.time() - t0) * 1000)
            if res.status_code == 200:
                self._discovery_cache["verified_models"][model_id] = {
                    "status": "verified",
                    "latency_ms": latency_ms,
                    "message": f"Verified active ({latency_ms}ms)",
                    "timestamp": time.time()
                }
                return {
                    "model_id": model_id,
                    "verified": True,
                    "status": "verified",
                    "latency_ms": latency_ms,
                    "message": f"Verified accessible ({latency_ms}ms)"
                }
            else:
                err_text = res.text
                try:
                    err_text = res.json().get("error", {}).get("message", res.text)
                except Exception:
                    pass
                self._discovery_cache["verified_models"][model_id] = {
                    "status": "unavailable",
                    "latency_ms": latency_ms,
                    "message": f"HTTP {res.status_code}: {err_text[:140]}",
                    "timestamp": time.time()
                }
                return {
                    "model_id": model_id,
                    "verified": False,
                    "status": "unavailable",
                    "code": res.status_code,
                    "latency_ms": latency_ms,
                    "message": err_text
                }
        except Exception as exc:
            return {
                "model_id": model_id,
                "verified": False,
                "status": "unavailable",
                "latency_ms": int((time.time() - t0) * 1000),
                "message": str(exc)
            }

    def list_models(self, verify_live: bool = False) -> List[Dict[str, Any]]:
        api_key, _ = get_server_gemini_api_key()
        discovered_ids, discovery_err = self._discover_account_models(api_key, force=verify_live)

        models_out: List[Dict[str, Any]] = []
        for entry in GEMINI_CURATED_CATALOG:
            m_id = entry["id"]
            item = dict(entry)
            item["is_default"] = (m_id == DEFAULT_GEMINI_MODEL)

            if not api_key:
                item["available"] = False
                item["verification_status"] = "unavailable"
                item["status_message"] = "API key not configured on server"
            else:
                cached_v = self._discovery_cache["verified_models"].get(m_id)
                if cached_v:
                    item["available"] = (cached_v["status"] == "verified")
                    item["verification_status"] = cached_v["status"]
                    item["status_message"] = cached_v["message"]
                    item["latency_ms"] = cached_v.get("latency_ms")
                elif discovered_ids:
                    if m_id in discovered_ids:
                        item["available"] = True
                        item["verification_status"] = "verified_in_catalog"
                        item["status_message"] = "Available in your Gemini account catalog"
                    else:
                        item["available"] = False
                        item["verification_status"] = "unavailable"
                        item["status_message"] = "Not listed in account's supported models"
                else:
                    # Configured fallback when discovery network call is offline
                    item["available"] = True
                    item["verification_status"] = "configured"
                    item["status_message"] = discovery_err or "Configured (pending live verification)"

            models_out.append(item)

        return models_out

    def is_model_allowed(self, model_id: str) -> Tuple[bool, str]:
        models = self.list_models(verify_live=False)
        for m in models:
            if m["id"] == model_id:
                if not m["available"]:
                    return False, m.get("status_message", f"Model '{model_id}' is currently unavailable.")
                return True, "OK"
        # Also check if it's in discovered account models
        api_key, _ = get_server_gemini_api_key()
        discovered_ids, _ = self._discover_account_models(api_key, force=False)
        if model_id in discovered_ids:
            return True, "OK"
        return False, f"Model '{model_id}' is not registered or supported by this server."

    def generate(
        self,
        model_id: str,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1200
    ) -> Tuple[bool, str, Dict[str, Any]]:
        api_key, _ = get_server_gemini_api_key()
        if not api_key:
            return False, "Server Gemini API key is not configured.", {"error_code": 401}

        allowed, reason = self.is_model_allowed(model_id)
        if not allowed:
            return False, reason, {"error_code": 400, "model_id": model_id}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": float(temperature),
                "maxOutputTokens": int(max_tokens)
            }
        }

        t0 = time.time()
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT_SECONDS)
            latency_ms = int((time.time() - t0) * 1000)

            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                    if text:
                        self._discovery_cache["verified_models"][model_id] = {
                            "status": "verified",
                            "latency_ms": latency_ms,
                            "message": f"Verified active ({latency_ms}ms)",
                            "timestamp": time.time()
                        }
                        return True, text, {"latency_ms": latency_ms, "model_id": model_id}
                return False, "Model returned an empty response.", {"error_code": 502, "latency_ms": latency_ms}
            else:
                err_code = res.status_code
                err_msg = res.text
                err_status = ""
                try:
                    err_obj = res.json().get("error", {})
                    err_msg = err_obj.get("message", res.text)
                    err_status = err_obj.get("status", "")
                except Exception:
                    pass

                friendly_error = f"Gemini API Error (HTTP {err_code}{f' {err_status}' if err_status else ''}): {err_msg}"
                return False, friendly_error, {"error_code": err_code, "latency_ms": latency_ms, "model_id": model_id}

        except requests.exceptions.Timeout:
            return False, f"Request to '{model_id}' timed out after {LLM_TIMEOUT_SECONDS}s.", {"error_code": 408}
        except requests.exceptions.ConnectionError:
            return False, "Network connection error while contacting Google Gemini API.", {"error_code": 503}
        except Exception as exc:
            return False, f"Unexpected LLM error: {str(exc)}", {"error_code": 500}


# Singleton registry instance
gemini_provider = GeminiLLMProvider()
