"""Thin wrapper around the OpenAI SDK with graceful offline fallback.

If no API key is configured the helpers raise a clear error for chat, but embeddings
fall back to a deterministic local hash so the RAG store can still be built/tested.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from openai import OpenAI

from app.core.config import settings

_client: OpenAI | None = None


def client() -> OpenAI:
    """OpenAI SDK client, pointed at the configured provider (OpenAI or Gemini).

    Gemini exposes an OpenAI-compatible endpoint, so the same SDK works for both —
    we just swap the base_url, api_key, and model names.
    """
    global _client
    if _client is None:
        # max_retries lets the SDK wait out 429s (respects Retry-After) — important on
        # free tiers like Groq (12k tokens/min) when a batch of emails arrives at once.
        _client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            max_retries=5,
        )
    return _client


def _no_key_error() -> RuntimeError:
    return RuntimeError(
        f"No LLM API key configured for provider '{settings.llm_provider}' — "
        "set GEMINI_API_KEY (or OPENAI_API_KEY) in backend/.env"
    )


def _extract_json(content: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating markdown ```json fences some models add."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    text = text.strip().strip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
        raise


def chat_json(system: str, user: str, *, temperature: float = 0.2) -> dict[str, Any]:
    """Call the chat model and parse a JSON object response."""
    if not settings.has_llm:
        raise _no_key_error()

    resp = client().chat.completions.create(
        model=settings.chat_model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return _extract_json(resp.choices[0].message.content)


def chat_text(system: str, user: str, *, temperature: float = 0.4) -> str:
    if not settings.has_llm:
        raise _no_key_error()

    resp = client().chat.completions.create(
        model=settings.chat_model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content.strip()


def embed(text: str) -> list[float]:
    """Return an embedding vector for `text`.

    Falls back to a deterministic pseudo-embedding when no API key is present so the
    vector store and retrieval pipeline remain testable offline.
    """
    # Use the provider's embeddings endpoint when available; otherwise (e.g. Groq) or
    # when no key is set, fall back to a deterministic local embedding.
    if settings.has_llm and settings.provider_has_embeddings:
        resp = client().embeddings.create(
            model=settings.embed_model, input=text[:8000]
        )
        return resp.data[0].embedding
    return _fallback_embedding(text)


def _fallback_embedding(text: str, dim: int = 256) -> list[float]:
    """Deterministic bag-of-words hash embedding (offline only)."""
    vec = [0.0] * dim
    for token in text.lower().split():
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]
