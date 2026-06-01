"""
forge.llm_router
================
Free LLM router for VoxelForge — inspired by apmantza/pi-free.

Routes requests to the best available free LLM provider automatically,
with a waterfall fallback chain.  Works with Claude Code and OpenCode
as an MCP-compatible generation backend.

Free providers supported (in priority order):
  1. Groq          — free tier, fastest inference (~500 tok/s)
  2. Cerebras      — free tier, ultra-fast (~1800 tok/s)
  3. SambaNova     — free tier, Llama 3.3 70B + DeepSeek
  4. NVIDIA NIM    — 1000 free req/month
  5. Gemini        — gemini-2.5-flash free tier
  6. OpenRouter    — 50+ free models (Llama, Mistral, Qwen, etc.)
  7. LLM7          — 100 req/hr, no credit card
  8. Together AI   — $1 trial, 138 chat models
  9. Ollama        — local inference (free if hardware available)
  10. Hugging Face — free inference API

Environment variables (any subset is enough — router picks what's available):
  GROQ_API_KEY
  CEREBRAS_API_KEY
  SAMBANOVA_API_KEY
  NVIDIA_API_KEY
  GEMINI_API_KEY
  OPENROUTER_API_KEY
  LLM7_API_KEY
  TOGETHER_API_KEY
  HF_API_KEY           (Hugging Face)
  OLLAMA_BASE_URL      (default: http://localhost:11434)

Usage
-----
>>> from forge.llm_router import LLMRouter
>>> router = LLMRouter()
>>> print(router.available_providers())
>>> response = router.chat("Write a short quest for a medieval RPG")
>>> print(response.text)
>>> print(response.provider, response.model)

# Force a specific provider
>>> response = router.chat("...", provider="groq")

# Force a task type (picks best model for that task)
>>> response = router.chat("...", task="code")    # coding task
>>> response = router.chat("...", task="creative") # creative writing
>>> response = router.chat("...", task="fast")     # latency-sensitive
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------

@dataclass
class ProviderDef:
    name:       str
    base_url:   str
    env_key:    str                    # env var holding the API key
    models:     Dict[str, str]         # task → model name
    priority:   int                    # lower = preferred
    headers_fn: Optional[str] = None   # special header strategy ("bearer"|"x-api-key"|"bearer-no-org")
    free_note:  str = ""


_PROVIDERS: List[ProviderDef] = [
    ProviderDef(
        name     = "groq",
        base_url = "https://api.groq.com/openai/v1",
        env_key  = "GROQ_API_KEY",
        priority = 1,
        models   = {
            "default":  "llama-3.3-70b-versatile",
            "fast":     "llama-3.1-8b-instant",
            "code":     "llama-3.3-70b-versatile",
            "creative": "llama-3.3-70b-versatile",
            "small":    "gemma2-9b-it",
        },
        free_note = "Free tier — no credit card needed",
    ),
    ProviderDef(
        name     = "cerebras",
        base_url = "https://api.cerebras.ai/v1",
        env_key  = "CEREBRAS_API_KEY",
        priority = 2,
        models   = {
            "default":  "llama-3.3-70b",
            "fast":     "llama3.1-8b",
            "code":     "llama-3.3-70b",
            "creative": "llama-3.3-70b",
            "small":    "llama3.1-8b",
        },
        free_note = "Free account — ~1800 tok/s",
    ),
    ProviderDef(
        name     = "sambanova",
        base_url = "https://fast-api.snova.ai/v1",
        env_key  = "SAMBANOVA_API_KEY",
        priority = 3,
        models   = {
            "default":  "Meta-Llama-3.3-70B-Instruct",
            "fast":     "Meta-Llama-3.1-8B-Instruct",
            "code":     "DeepSeek-V3-0324",
            "creative": "Meta-Llama-3.3-70B-Instruct",
            "small":    "Meta-Llama-3.1-8B-Instruct",
        },
        free_note = "Free — no credit card, 20-480 RPM",
    ),
    ProviderDef(
        name     = "nvidia",
        base_url = "https://integrate.api.nvidia.com/v1",
        env_key  = "NVIDIA_API_KEY",
        priority = 4,
        models   = {
            "default":  "meta/llama-3.3-70b-instruct",
            "fast":     "meta/llama-3.1-8b-instruct",
            "code":     "qwen/qwen2.5-coder-32b-instruct",
            "creative": "meta/llama-3.3-70b-instruct",
            "small":    "meta/llama-3.1-8b-instruct",
        },
        free_note = "1000 free req/month via NIM",
    ),
    ProviderDef(
        name     = "gemini",
        base_url = "https://generativelanguage.googleapis.com/v1beta",
        env_key  = "GEMINI_API_KEY",
        priority = 5,
        models   = {
            "default":  "gemini-2.5-flash",
            "fast":     "gemini-2.0-flash",
            "code":     "gemini-2.5-flash",
            "creative": "gemini-2.5-flash",
            "small":    "gemini-2.0-flash-lite",
        },
        headers_fn = "gemini",
        free_note  = "Free tier — 1500 req/day",
    ),
    ProviderDef(
        name     = "openrouter",
        base_url = "https://openrouter.ai/api/v1",
        env_key  = "OPENROUTER_API_KEY",
        priority = 6,
        models   = {
            "default":  "meta-llama/llama-3.3-70b-instruct:free",
            "fast":     "meta-llama/llama-3.1-8b-instruct:free",
            "code":     "deepseek/deepseek-r1:free",
            "creative": "mistralai/mistral-7b-instruct:free",
            "small":    "qwen/qwen-2.5-7b-instruct:free",
        },
        free_note = "50+ free models — free API key",
    ),
    ProviderDef(
        name     = "llm7",
        base_url = "https://api.llm7.io/v1",
        env_key  = "LLM7_API_KEY",
        priority = 7,
        models   = {
            "default":  "gpt-4o",
            "fast":     "gpt-4o-mini",
            "code":     "gpt-4o",
            "creative": "gpt-4o",
            "small":    "gpt-4o-mini",
        },
        free_note = "100 req/hr — no credit card",
    ),
    ProviderDef(
        name     = "together",
        base_url = "https://api.together.xyz/v1",
        env_key  = "TOGETHER_API_KEY",
        priority = 8,
        models   = {
            "default":  "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "fast":     "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "code":     "deepseek-ai/DeepSeek-V3",
            "creative": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "small":    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        },
        free_note = "$1 trial credit — 138 models",
    ),
    ProviderDef(
        name     = "huggingface",
        base_url = "https://api-inference.huggingface.co/models",
        env_key  = "HF_API_KEY",
        priority = 9,
        models   = {
            "default":  "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "fast":     "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "code":     "Qwen/Qwen2.5-Coder-7B-Instruct",
            "creative": "mistralai/Mistral-7B-Instruct-v0.3",
            "small":    "microsoft/Phi-3-mini-4k-instruct",
        },
        headers_fn = "hf",
        free_note  = "Free inference API",
    ),
    ProviderDef(
        name     = "ollama",
        base_url = "",   # set dynamically from OLLAMA_BASE_URL
        env_key  = "OLLAMA_BASE_URL",
        priority = 10,
        models   = {
            "default":  "llama3.2",
            "fast":     "llama3.2",
            "code":     "codellama",
            "creative": "llama3.2",
            "small":    "phi3",
        },
        free_note = "Local inference — free if hardware available",
    ),
    # VoxelForge built-in llama.cpp server (highest priority when running)
    ProviderDef(
        name     = "local",
        base_url = "",   # set from VFE_INFERENCE_URL env var or default port
        env_key  = "VFE_INFERENCE_URL",
        priority = 0,   # always try first if configured
        models   = {
            "default":  "local-model",
            "fast":     "local-model",
            "code":     "local-model",
            "creative": "local-model",
            "small":    "local-model",
        },
        free_note = "VoxelForge local llama.cpp server (offline, free)",
    ),
]

_PROVIDER_MAP: Dict[str, ProviderDef] = {p.name: p for p in _PROVIDERS}


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    text:       str
    provider:   str
    model:      str
    tokens_in:  int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    error:      Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.text)

    def __str__(self) -> str:
        return self.text


# ---------------------------------------------------------------------------
# Free-model detection (pi-free isFreeModel pattern)
# ---------------------------------------------------------------------------

_FREE_SIGNALS = (":free", "-free", "free-", "/free", "free_")

def is_free_model(model_id: str, provider: str) -> bool:
    """
    Heuristic: return True if a model is likely free.
    Mirrors the isFreeModel() logic from pi-free.
    """
    ml = model_id.lower()
    if any(s in ml for s in _FREE_SIGNALS):
        return True
    # Providers where all listed models are free
    if provider in ("groq", "cerebras", "sambanova", "llm7", "ollama"):
        return True
    # Gemini free models
    if provider == "gemini" and "gemini-2." in ml:
        return True
    return False


# ---------------------------------------------------------------------------
# LLMRouter
# ---------------------------------------------------------------------------

class LLMRouter:
    """
    Automatically routes LLM requests to the best available free provider.

    Parameters
    ----------
    preferred_provider : str, optional
        Always try this provider first (e.g. "groq").
    prefer_free_only : bool
        Only use providers with confirmed free tiers (default True).
    timeout : int
        Request timeout in seconds.
    verbose : bool
        Print provider selection and latency info.
    """

    def __init__(
        self,
        preferred_provider: Optional[str] = None,
        prefer_free_only:   bool          = True,
        timeout:            int           = 60,
        verbose:            bool          = False,
    ):
        self.preferred   = preferred_provider
        self.free_only   = prefer_free_only
        self.timeout     = timeout
        self.verbose     = verbose
        self._cache: Dict[str, str] = {}   # provider → last working model

    # ------------------------------------------------------------------
    def available_providers(self) -> List[Dict[str, str]]:
        """Return providers that have an API key set in the environment."""
        avail = []
        for p in _PROVIDERS:
            key_val = self._get_key(p)
            if key_val:
                avail.append({
                    "name":     p.name,
                    "priority": p.priority,
                    "free":     p.free_note,
                    "models":   list(p.models.values()),
                })
        return avail

    def has_any_provider(self) -> bool:
        return len(self.available_providers()) > 0

    # ------------------------------------------------------------------
    def chat(
        self,
        prompt:         str,
        system:         Optional[str] = None,
        provider:       Optional[str] = None,
        task:           str           = "default",
        temperature:    float         = 0.7,
        max_tokens:     int           = 2048,
        stream:         bool          = False,
    ) -> LLMResponse:
        """
        Send a chat prompt and return the first successful response.

        Parameters
        ----------
        prompt : str
            User message.
        system : str, optional
            System prompt.
        provider : str, optional
            Force a specific provider ("groq", "gemini", etc.).
        task : str
            Hint for model selection: default | fast | code | creative | small.
        temperature : float
        max_tokens : int

        Returns
        -------
        LLMResponse
        """
        chain = self._build_chain(provider)

        for pdef in chain:
            key = self._get_key(pdef)
            if not key:
                continue
            model = pdef.models.get(task, pdef.models["default"])
            if self.verbose:
                print(f"[LLMRouter] Trying {pdef.name} / {model}")
            try:
                resp = self._call(pdef, key, model, prompt, system,
                                   temperature, max_tokens)
                if resp.ok:
                    if self.verbose:
                        print(f"[LLMRouter] OK from {pdef.name} in {resp.latency_ms}ms")
                    return resp
                if self.verbose:
                    print(f"[LLMRouter] {pdef.name} returned empty: {resp.error}")
            except Exception as exc:
                if self.verbose:
                    print(f"[LLMRouter] {pdef.name} error: {exc}")
                continue

        return LLMResponse(
            text     = "",
            provider = "none",
            model    = "",
            error    = "All providers failed or no API key found",
        )

    def complete(
        self,
        prompt:      str,
        task:        str   = "default",
        max_tokens:  int   = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Convenience wrapper — returns plain text or empty string."""
        return self.chat(prompt, task=task, max_tokens=max_tokens,
                         temperature=temperature).text

    # ------------------------------------------------------------------
    # Provider chain builder
    # ------------------------------------------------------------------

    def _build_chain(self, override: Optional[str]) -> List[ProviderDef]:
        """Return ordered list of providers to try."""
        if override:
            pdef = _PROVIDER_MAP.get(override)
            if not pdef:
                raise ValueError(f"Unknown provider: {override!r}. "
                                  f"Valid: {list(_PROVIDER_MAP)}")
            return [pdef]
        # Sort by priority; preferred first
        chain = sorted(_PROVIDERS, key=lambda p: (
            0 if p.name == self.preferred else 1,
            p.priority,
        ))
        return chain

    # ------------------------------------------------------------------
    # HTTP dispatch per provider
    # ------------------------------------------------------------------

    def _call(
        self,
        pdef:        ProviderDef,
        key:         str,
        model:       str,
        prompt:      str,
        system:      Optional[str],
        temperature: float,
        max_tokens:  int,
    ) -> LLMResponse:
        """Dispatch to the right call strategy for this provider."""
        if pdef.name == "gemini":
            return self._call_gemini(key, model, prompt, system,
                                      temperature, max_tokens)
        if pdef.name == "huggingface":
            return self._call_hf(key, model, prompt, system, max_tokens)
        if pdef.name == "ollama":
            base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            return self._call_openai_compat(
                f"{base}/api", key or "ollama", model,
                prompt, system, temperature, max_tokens,
                auth_type="none",
            )
        # Default: OpenAI-compatible endpoint
        return self._call_openai_compat(
            pdef.base_url, key, model,
            prompt, system, temperature, max_tokens,
        )

    def _call_openai_compat(
        self,
        base_url:    str,
        key:         str,
        model:       str,
        prompt:      str,
        system:      Optional[str],
        temperature: float,
        max_tokens:  int,
        auth_type:   str = "bearer",
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {"Content-Type": "application/json"}
        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {key}"
        elif auth_type == "x-api-key":
            headers["x-api-key"] = key
        # auth_type == "none" → no auth header (Ollama local)

        t0 = time.time()
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers = headers,
            json    = {
                "model":       model,
                "messages":    messages,
                "temperature": temperature,
                "max_tokens":  max_tokens,
            },
            timeout = self.timeout,
        )

        latency = int((time.time() - t0) * 1000)

        if resp.status_code != 200:
            return LLMResponse(
                text     = "",
                provider = base_url,
                model    = model,
                latency_ms = latency,
                error    = f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

        data   = resp.json()
        text   = (data.get("choices", [{}])[0]
                      .get("message", {})
                      .get("content", ""))
        usage  = data.get("usage", {})
        return LLMResponse(
            text       = text.strip(),
            provider   = base_url,
            model      = model,
            tokens_in  = usage.get("prompt_tokens", 0),
            tokens_out = usage.get("completion_tokens", 0),
            latency_ms = latency,
        )

    def _call_gemini(
        self,
        key:         str,
        model:       str,
        prompt:      str,
        system:      Optional[str],
        temperature: float,
        max_tokens:  int,
    ) -> LLMResponse:
        """Gemini uses a different REST schema."""
        contents = []
        if system:
            # Gemini uses systemInstruction separately
            pass
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature":    temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}

        t0 = time.time()
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{model}:generateContent?key={key}")
        resp = requests.post(url, json=body, timeout=self.timeout,
                             headers={"Content-Type": "application/json"})
        latency = int((time.time() - t0) * 1000)

        if resp.status_code != 200:
            return LLMResponse(
                text="", provider="gemini", model=model, latency_ms=latency,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        text = (data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", ""))
        return LLMResponse(text=text.strip(), provider="gemini", model=model,
                           latency_ms=latency)

    def _call_hf(
        self,
        key:      str,
        model:    str,
        prompt:   str,
        system:   Optional[str],
        max_toks: int,
    ) -> LLMResponse:
        """Hugging Face serverless inference."""
        full = (system + "\n\n" + prompt) if system else prompt
        t0 = time.time()
        resp = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers = {"Authorization": f"Bearer {key}",
                       "Content-Type": "application/json"},
            json    = {"inputs": full,
                       "parameters": {"max_new_tokens": max_toks,
                                      "return_full_text": False}},
            timeout = self.timeout,
        )
        latency = int((time.time() - t0) * 1000)
        if resp.status_code != 200:
            return LLMResponse(text="", provider="huggingface", model=model,
                               latency_ms=latency,
                               error=f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if isinstance(data, list):
            text = data[0].get("generated_text", "")
        else:
            text = data.get("generated_text", "")
        return LLMResponse(text=text.strip(), provider="huggingface", model=model,
                           latency_ms=latency)

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _get_key(self, pdef: ProviderDef) -> str:
        """Return the API key for a provider (env var or fallback chain)."""
        val = os.environ.get(pdef.env_key, "")
        if pdef.name == "ollama":
            url = os.environ.get("OLLAMA_BASE_URL", "")
            return url or ""
        if pdef.name == "local":
            # Local llama.cpp: use VFE_INFERENCE_URL or default to localhost:8090
            url = os.environ.get("VFE_INFERENCE_URL", "")
            if not url:
                # Auto-detect: try to ping the default local port
                try:
                    requests.get("http://localhost:8090/health", timeout=0.5)
                    return "http://localhost:8090"  # non-empty = available
                except Exception:
                    return ""  # not running
            return url
        # Also accept generic LLM_API_KEY as universal fallback
        if not val and pdef.name in ("groq", "together", "openrouter"):
            val = os.environ.get("LLM_API_KEY", "")
        return val


# ---------------------------------------------------------------------------
# List free models via OpenRouter discovery
# ---------------------------------------------------------------------------

def fetch_free_openrouter_models(api_key: str = "") -> List[Dict[str, Any]]:
    """
    Fetch all free models from OpenRouter.
    No API key needed for listing; key is optional for filtering.
    Returns list of {"id", "name", "context_length"} dicts.
    """
    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=15,
        )
        resp.raise_for_status()
        models = resp.json().get("data", [])
        free = []
        for m in models:
            pricing = m.get("pricing", {})
            prompt_cost = float(pricing.get("prompt", "1") or "1")
            if prompt_cost == 0 or ":free" in m.get("id", ""):
                free.append({
                    "id":             m.get("id", ""),
                    "name":           m.get("name", ""),
                    "context_length": m.get("context_length", 0),
                    "provider":       "openrouter",
                })
        return free
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Convenience singleton
# ---------------------------------------------------------------------------

_default_router: Optional[LLMRouter] = None


def get_router(verbose: bool = False) -> LLMRouter:
    """Return a module-level cached router instance."""
    global _default_router
    if _default_router is None:
        preferred = os.environ.get("LLM_PROVIDER", "")
        _default_router = LLMRouter(
            preferred_provider = preferred or None,
            verbose            = verbose,
        )
    return _default_router


def llm(
    prompt:      str,
    system:      Optional[str] = None,
    task:        str           = "default",
    max_tokens:  int           = 2048,
    temperature: float         = 0.7,
) -> str:
    """
    One-line LLM call — auto-routes to best available free provider.

    Returns the response text, or empty string if all providers fail.

    >>> from forge.llm_router import llm
    >>> story = llm("Write a 3-sentence intro for a dungeon game", task="creative")
    """
    return get_router().complete(prompt, task=task, max_tokens=max_tokens,
                                  temperature=temperature)


# ---------------------------------------------------------------------------
# Claude Code / OpenCode tool definitions
# ---------------------------------------------------------------------------

#: OpenAI-compatible function-calling schema for the LLM router itself.
#: Include in any Claude Code session to give the agent routing control.
ROUTING_TOOL = {
    "type": "function",
    "function": {
        "name": "route_llm",
        "description": (
            "Send a prompt to the best available free LLM and return the text response. "
            "Automatically selects from Groq, Cerebras, SambaNova, NVIDIA NIM, Gemini, "
            "OpenRouter free models, LLM7, Together AI, or local Ollama."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt":   {"type": "string", "description": "The user prompt"},
                "system":   {"type": "string", "description": "Optional system prompt"},
                "task":     {"type": "string",
                              "enum": ["default", "fast", "code", "creative", "small"],
                              "description": "Task type for model selection"},
                "provider": {"type": "string",
                              "description": "Force a specific provider (optional)"},
                "max_tokens": {"type": "integer", "default": 2048},
                "temperature": {"type": "number", "default": 0.7},
            },
            "required": ["prompt"],
        },
    },
}
