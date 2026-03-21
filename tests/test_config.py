"""Unit tests for config.py environment switching."""
from config import Environment, ENVIRONMENT, USE_LOCAL_MODELS, EMBED_BASE_URL


def test_default_environment_is_local():
    assert ENVIRONMENT == Environment.LOCAL

def test_local_environment_uses_local_models():
    assert USE_LOCAL_MODELS is True

def test_environment_enum_values():
    assert Environment.LOCAL == "local"
    assert Environment.GCP == "gcp"

def test_local_has_ollama_config():
    assert "localhost" in EMBED_BASE_URL or "11434" in EMBED_BASE_URL
