"""Unit tests for config.py environment switching.

Updated Week 1: Environment enum replaced with plain string constant.
USE_LOCAL_MODELS replaced with MODEL_STRING / EMBED_MODEL comparison.
EMBED_BASE_URL replaced with OLLAMA_BASE_URL.
"""
from config import (
    ENVIRONMENT,
    MODEL_STRING,
    EMBED_MODEL,
    OLLAMA_BASE_URL,
    LOCAL_MODEL,
    LOCAL_EMBED,
    PROD_MODEL,
    PROD_EMBED,
)


def test_default_environment_is_local():
    """Default ENVIRONMENT must be 'local' when no env var is set."""
    assert ENVIRONMENT == "local"


def test_environment_is_valid_value():
    """ENVIRONMENT must be one of the two valid values."""
    assert ENVIRONMENT in ("local", "gcp")


def test_local_environment_uses_local_models():
    """In local mode, MODEL_STRING must point to the local model."""
    if ENVIRONMENT == "local":
        assert MODEL_STRING == LOCAL_MODEL
    else:
        assert MODEL_STRING == PROD_MODEL


def test_local_environment_uses_local_embeddings():
    """In local mode, EMBED_MODEL must point to the local embedding model."""
    if ENVIRONMENT == "local":
        assert EMBED_MODEL == LOCAL_EMBED
    else:
        assert EMBED_MODEL == PROD_EMBED


def test_ollama_base_url_is_localhost():
    """OLLAMA_BASE_URL must point to localhost Ollama instance."""
    assert "localhost" in OLLAMA_BASE_URL or "11434" in OLLAMA_BASE_URL


def test_model_strings_are_pinned():
    """Model strings must be version-pinned — no 'latest' aliases."""
    assert "latest" not in LOCAL_MODEL
    assert "latest" not in PROD_MODEL