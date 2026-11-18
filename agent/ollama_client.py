"""
Local Ollama LLM Client optimized for 2020 Mac hardware (Apple M1 & Intel Core i5/i7).
Keeps unified memory / RAM usage low via bounded context windows (num_ctx=4096)
and supports automatic fallback if Ollama is not currently running.
"""

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

# Curated model profiles specifically benchmarked for 2020 MacBook Air / Pro / Mac mini
MAC_2020_MODEL_PROFILES: List[Dict[str, Any]] = [
    {
        "id": "qwen2.5:3b",
        "name": "Qwen 2.5 (3B) – Ajánlott 2020-as Mac-hez",
        "ram_required": "~1.9 GB RAM",
        "mac_compatibility": "Tökéletes 2020 M1 (8GB/16GB) és 2020 Intel (8GB+) Mac-re",
        "speed_note": "Nagyon gyors, kiváló magyar és angol nyelvi megértés",
        "recommended": True,
    },
    {
        "id": "llama3.2:3b",
        "name": "Llama 3.2 (3B) – Gyors Apple Silicon profil",
        "ram_required": "~2.0 GB RAM",
        "mac_compatibility": "Ideális 2020-as M1 MacBook Air / Pro (8GB/16GB) gépekre",
        "speed_note": "Kifejezetten gyors összegzés és strukturált adatkinyerés",
        "recommended": False,
    },
    {
        "id": "qwen2.5:1.5b",
        "name": "Qwen 2.5 (1.5B) – Ultrakönnyű / Intel Mac mód",
        "ram_required": "~1.0 GB RAM",
        "mac_compatibility": "2020-as Intel i5/i7 Mac (8GB RAM) + sok megnyitott böngészőfül mellé",
        "speed_note": "Minimális processzor- és ventilátorterhelés",
        "recommended": False,
    },
    {
        "id": "qwen2.5:7b",
        "name": "Qwen 2.5 (7B) – Mélyelemző mód (16GB RAM)",
        "ram_required": "~4.7 GB RAM",
        "mac_compatibility": "Csak 16 GB RAM-mal szerelt 2020-as M1 vagy Intel Mac-re ajánlott",
        "speed_note": "Részletesebb összehasonlító érvelés és tantervelemzés",
        "recommended": False,
    },
]


class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or DEFAULT_OLLAMA_HOST).rstrip("/")
        self.model = model or DEFAULT_MODEL
        # Low-memory parameters tuned for 2020 Macs
        self.default_options = {
            "num_ctx": 4096,
            "temperature": 0.15,
            "top_p": 0.9,
        }

    def check_status(self) -> Dict[str, Any]:
        """Check if local Ollama daemon is reachable and list installed models."""
        url = f"{self.base_url}/api/tags"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                active_model = self.model
                if models and active_model not in models:
                    # Pick first installed model if default isn't pulled yet
                    active_model = models[0]
                return {
                    "online": True,
                    "host": self.base_url,
                    "configured_model": self.model,
                    "active_model": active_model,
                    "installed_models": models,
                    "recommended_profiles": MAC_2020_MODEL_PROFILES,
                    "mode": "Local Ollama LLM (Active)",
                }
        except Exception as exc:
            return {
                "online": False,
                "host": self.base_url,
                "configured_model": self.model,
                "active_model": self.model,
                "installed_models": [],
                "recommended_profiles": MAC_2020_MODEL_PROFILES,
                "mode": "Hibrid Determinisztikus Elemző (Ollama offline – indítsd el: `ollama serve`)",
                "error": str(exc),
            }

    def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Trigger model download on the local Ollama server."""
        url = f"{self.base_url}/api/pull"
        payload = json.dumps({"name": model_name, "stream": False}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                self.model = model_name
                return {"ok": True, "model": model_name, "status": body.get("status", "success")}
        except Exception as exc:
            return {"ok": False, "model": model_name, "error": str(exc)}

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        json_mode: bool = False,
        timeout: float = 45.0,
    ) -> Tuple[bool, str, str]:
        """
        Send a chat completion request to local Ollama.
        Returns (success, response_text, used_model_name).
        """
        status = self.check_status()
        if not status["online"]:
            return False, "", "offline"

        used_model = model or status["active_model"] or self.model
        payload_dict: Dict[str, Any] = {
            "model": used_model,
            "messages": messages,
            "stream": False,
            "keep_alive": "10m",
            "options": self.default_options,
        }
        if json_mode:
            payload_dict["format"] = "json"

        data = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                content = raw.get("message", {}).get("content", "")
                return True, content, used_model
        except Exception as exc:
            return False, str(exc), used_model

    @staticmethod
    def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
        """Safely parse JSON from small local model outputs (3B/7B)."""
        if not text:
            return None
        cleaned = text.strip()
        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # Locate outermost {...}
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception:
                return None
        return None
