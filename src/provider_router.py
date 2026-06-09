from __future__ import annotations
from dataclasses import dataclass
import os, time
from dotenv import load_dotenv
load_dotenv()

@dataclass
class ModelResult:
    ok: bool
    text: str
    provider: str
    model: str
    latency_ms: int
    error: str = ""

class ProviderRouter:
    def __init__(self) -> None:
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip()
        self.default_provider = os.getenv("DEFAULT_PROVIDER", "auto").strip().lower()

    @property
    def status(self) -> str:
        if self.gemini_key:
            return f"AI configured · Gemini · {self.gemini_model}"
        if self.anthropic_key:
            return f"AI configured · Anthropic · {self.anthropic_model}"
        return "Local mode · no API key required"

    def generate(self, prompt: str, system: str = "", provider: str = "auto", temperature: float = 0.2) -> ModelResult:
        chosen = (provider or self.default_provider or "auto").lower()
        if chosen == "auto":
            if self.gemini_key:
                chosen = "gemini"
            elif self.anthropic_key:
                chosen = "anthropic"
            else:
                chosen = "local"
        if chosen == "gemini" and self.gemini_key:
            return self._gemini(prompt, system, temperature)
        if chosen in {"anthropic", "claude"} and self.anthropic_key:
            return self._anthropic(prompt, system, temperature)
        return ModelResult(True, self._local_response(prompt), "local", "heuristic", 0)

    def _gemini(self, prompt: str, system: str, temperature: float) -> ModelResult:
        start = time.time()
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel(self.gemini_model, system_instruction=system or "You are a precise document intelligence assistant.")
            resp = model.generate_content(prompt, generation_config={"temperature": temperature, "max_output_tokens": 1800})
            return ModelResult(True, getattr(resp, "text", "").strip(), "gemini", self.gemini_model, int((time.time() - start) * 1000))
        except Exception as exc:
            return ModelResult(False, self._local_response(prompt), "gemini", self.gemini_model, int((time.time() - start) * 1000), str(exc))

    def _anthropic(self, prompt: str, system: str, temperature: float) -> ModelResult:
        start = time.time()
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=self.anthropic_key)
            msg = client.messages.create(model=self.anthropic_model, max_tokens=1800, temperature=temperature, system=system or "You are a precise document intelligence assistant.", messages=[{"role": "user", "content": prompt}])
            text = "\n".join([getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text"]).strip()
            return ModelResult(True, text, "anthropic", self.anthropic_model, int((time.time() - start) * 1000))
        except Exception as exc:
            return ModelResult(False, self._local_response(prompt), "anthropic", self.anthropic_model, int((time.time() - start) * 1000), str(exc))

    def _local_response(self, prompt: str) -> str:
        return "Local document intelligence response generated from keyword search, rule validation, and citation snippets. Configure an optional AI provider for richer synthesis."
