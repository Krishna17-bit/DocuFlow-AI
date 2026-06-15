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
        self.refresh_keys()

    def refresh_keys(self) -> None:
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022").strip()
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.default_provider = os.getenv("DEFAULT_PROVIDER", "auto").strip().lower()

        # Dynamic override from Streamlit session state if available
        try:
            import streamlit as st
            if "ui_gemini_key" in st.session_state and st.session_state.ui_gemini_key:
                self.gemini_key = st.session_state.ui_gemini_key.strip()
            if "ui_anthropic_key" in st.session_state and st.session_state.ui_anthropic_key:
                self.anthropic_key = st.session_state.ui_anthropic_key.strip()
            if "ui_openai_key" in st.session_state and st.session_state.ui_openai_key:
                self.openai_key = st.session_state.ui_openai_key.strip()
            if "ui_gemini_model" in st.session_state and st.session_state.ui_gemini_model:
                self.gemini_model = st.session_state.ui_gemini_model.strip()
            if "ui_anthropic_model" in st.session_state and st.session_state.ui_anthropic_model:
                self.anthropic_model = st.session_state.ui_anthropic_model.strip()
            if "ui_openai_model" in st.session_state and st.session_state.ui_openai_model:
                self.openai_model = st.session_state.ui_openai_model.strip()
        except Exception:
            pass

    @property
    def status(self) -> str:
        self.refresh_keys()
        active = []
        if self.openai_key:
            active.append(f"OpenAI ({self.openai_model})")
        if self.gemini_key:
            active.append(f"Gemini ({self.gemini_model})")
        if self.anthropic_key:
            active.append(f"Anthropic ({self.anthropic_model})")
        
        if active:
            return "Active APIs: " + " · ".join(active)
        return "Local Mode (no API keys configured)"

    def generate(self, prompt: str, system: str = "", provider: str = "auto", temperature: float = 0.2) -> ModelResult:
        self.refresh_keys()
        chosen = (provider or self.default_provider or "auto").lower()
        if chosen == "auto":
            if self.openai_key:
                chosen = "openai"
            elif self.gemini_key:
                chosen = "gemini"
            elif self.anthropic_key:
                chosen = "anthropic"
            else:
                chosen = "local"
        
        if chosen == "openai" and self.openai_key:
            return self._openai(prompt, system, temperature)
        if chosen == "gemini" and self.gemini_key:
            return self._gemini(prompt, system, temperature)
        if chosen in {"anthropic", "claude"} and self.anthropic_key:
            return self._anthropic(prompt, system, temperature)
            
        return ModelResult(True, self._local_response(prompt), "local", "heuristic", 0)

    def _openai(self, prompt: str, system: str, temperature: float) -> ModelResult:
        import urllib.request
        import json
        start = time.time()
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            post_data = {
                "model": self.openai_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1800
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(post_data).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            text = result["choices"][0]["message"]["content"].strip()
            return ModelResult(True, text, "openai", self.openai_model, int((time.time() - start) * 1000))
        except Exception as exc:
            return ModelResult(False, self._local_response(prompt), "openai", self.openai_model, int((time.time() - start) * 1000), str(exc))

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

