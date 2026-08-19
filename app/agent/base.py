"""LLM client wrapper.

Uses the OpenAI Python SDK pointed at a provider-specific OpenAI-compatible
endpoint, so the rest of the codebase stays provider-agnostic.

Provider resolution order:
  1. GROQ_API_KEY  -> Groq (recommended, free, no billing)
  2. GEMINI_API_KEY -> Google AI Studio
  3. OPENAI_API_KEY -> OpenAI (paid)
You can also force a custom endpoint via LLM_BASE_URL.

Model resolution:
  Groq periodically decommissions models (returning 404 model_not_found).
  We support a fallback chain: LLM_MODEL is tried first, then each entry in
  LLM_MODEL_FALLBACKS (comma-separated). The first model that works is
  cached for the rest of the run and logged loudly so ops can update the
  primary.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from openai import NotFoundError, OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import LLM_MODEL, LLM_MODEL_FALLBACKS


log = logging.getLogger(__name__)


_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _resolve_client_config() -> Tuple[str, Optional[str]]:
    """Return (api_key, base_url) for the first configured provider."""
    explicit_base = os.getenv("LLM_BASE_URL")

    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if groq_key:
        return groq_key, explicit_base or _GROQ_BASE_URL
    if gemini_key:
        return gemini_key, explicit_base or _GEMINI_BASE_URL
    if openai_key:
        return openai_key, explicit_base  # None => OpenAI default
    raise RuntimeError(
        "No LLM key found. Set GROQ_API_KEY (recommended, free) — "
        "or GEMINI_API_KEY / OPENAI_API_KEY."
    )


# Process-wide cache: once a model works for this run, keep using it.
_active_model: Optional[str] = None


def _model_chain() -> List[str]:
    """Ordered list of models to try: primary first, then fallbacks."""
    chain = [LLM_MODEL]
    for m in LLM_MODEL_FALLBACKS:
        if m and m not in chain:
            chain.append(m)
    return chain


class BaseAgent:
    """LLM-backed agent.

    Subclasses set `system_prompt` and call `complete()` / `complete_json()`.
    """

    system_prompt: str = "You are a helpful assistant."
    temperature: float = 0.2

    def __init__(self, client: Optional[OpenAI] = None):
        if client is not None:
            self.client = client
        else:
            api_key, base_url = _resolve_client_config()
            self.client = OpenAI(api_key=api_key, base_url=base_url)

    @property
    def model(self) -> str:
        return _active_model or LLM_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def _chat(self, messages, *, response_format: Optional[dict] = None) -> str:
        global _active_model
        last_exc: Optional[Exception] = None

        # Try the cached model first; fall back to the chain only if it 404s.
        candidates = [_active_model] if _active_model else _model_chain()
        for model_name in candidates:
            if model_name is None:
                continue
            kwargs: Dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "temperature": self.temperature,
            }
            if response_format is not None:
                kwargs["response_format"] = response_format
            try:
                resp = self.client.chat.completions.create(**kwargs)
                if _active_model != model_name:
                    if _active_model is not None:
                        log.warning(
                            "LLM model changed: '%s' -> '%s' (previous unavailable)",
                            _active_model,
                            model_name,
                        )
                    _active_model = model_name
                return resp.choices[0].message.content or ""
            except NotFoundError as e:
                log.warning(
                    "Model '%s' not available (404 model_not_found). "
                    "Trying next in fallback chain.",
                    model_name,
                )
                last_exc = e
                # If we had cached this model, invalidate and restart the search.
                if _active_model == model_name:
                    _active_model = None
                    candidates = _model_chain()
                continue

        raise RuntimeError(
            f"All models exhausted. Tried: {_model_chain()}. "
            f"Update LLM_MODEL / LLM_MODEL_FALLBACKS (see https://console.groq.com/docs/models)."
        ) from last_exc

    def complete(self, user_prompt: str) -> str:
        return self._chat(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

    def complete_json(self, user_prompt: str) -> dict:
        raw = self._chat(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.error("Model returned non-JSON: %s", raw[:200])
            raise
