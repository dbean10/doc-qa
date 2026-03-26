"""
lab4/rag/embedder.py

Embedding layer — converts text to vectors.

Local dev:  nomic-embed-text via Ollama (zero cost, already in your stack)
Production: text-embedding-3-large via OpenAI API

Riley's rule: the model used at index time and at query time must be identical.
If you change EMBED_MODEL, you must re-index all documents. There is no
migration path — the vector spaces are incompatible.

The embed() function is the only public interface. Everything else in the
RAG stack calls embed() — nothing calls Ollama or OpenAI directly.
"""

from __future__ import annotations

import os
import httpx


# ---------------------------------------------------------------------------
# Config — mirrors the LOCAL/PRODUCTION split from config.py
# ---------------------------------------------------------------------------

ENVIRONMENT = os.environ.get("ENVIRONMENT", "local").lower()

# These must match what was used when the Chroma collection was built.
LOCAL_EMBED_MODEL = "nomic-embed-text"
PROD_EMBED_MODEL = "text-embedding-3-large"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def embed(text: str) -> list[float]:
    """
    Convert a text string to an embedding vector.

    Uses nomic-embed-text locally (via Ollama) or text-embedding-3-large
    in production (via OpenAI API), selected by the ENVIRONMENT variable.

    Args:
        text: The text to embed. Should be a single chunk or query string.

    Returns:
        List of floats representing the embedding vector.

    Raises:
        ValueError: If text is empty.
        RuntimeError: If the embedding API call fails.
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")

    if ENVIRONMENT == "local":
        return _embed_ollama(text.strip())
    else:
        return _embed_openai(text.strip())


def get_model_name() -> str:
    """Return the active embedding model name. Used by store.py metadata."""
    return LOCAL_EMBED_MODEL if ENVIRONMENT == "local" else PROD_EMBED_MODEL


# ---------------------------------------------------------------------------
# Local implementation — Ollama
# ---------------------------------------------------------------------------

def _embed_ollama(text: str) -> list[float]:
    """
    Call Ollama's /api/embeddings endpoint.
    Requires: ollama serve && ollama pull nomic-embed-text
    """
    try:
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": LOCAL_EMBED_MODEL, "prompt": text},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Ollama embedding failed. Is 'ollama serve' running? Error: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Production implementation — OpenAI text-embedding-3-large
# ---------------------------------------------------------------------------

def _embed_openai(text: str) -> list[float]:
    """
    Call OpenAI's embeddings endpoint.
    Requires: OPENAI_API_KEY environment variable.

    Production note: batch embed at index time to reduce API calls.
    Single-call embed at query time is fine (one query per user turn).
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Required for production embeddings."
        )

    try:
        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": PROD_EMBED_MODEL, "input": text},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except httpx.HTTPError as exc:
        raise RuntimeError(f"OpenAI embedding failed: {exc}") from exc
