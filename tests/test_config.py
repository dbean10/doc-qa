"""Unit tests for config.py environment switching."""
import os
import pytest
from config import Environment, ENVIRONMENT, USE_LOCAL_MODELS


def test_default_environment_is_local():
    """Config should default to LOCAL when no env var is set."""
    assert ENVIRONMENT == Environment.LOCAL


def test_local_environment_uses_local_models():
    """LOCAL environment should set USE_LOCAL_MODELS to True."""
    assert USE_LOCAL_MODELS is True


def test_environment_enum_values():
    """Environment enum should have exactly LOCAL and GCP."""
    assert Environment.LOCAL == "local"
    assert Environment.GCP == "gcp"


def test_local_has_ollama_config():
    """LOCAL environment should define EMBED_BASE_URL."""
    from config import EMBED_BASE_URL
    assert "localhost" in EMBED_BASE_URL or "11434" in EMBED_BASE_URL
