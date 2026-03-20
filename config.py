import os
from enum import Enum

class Environment(str, Enum):
    LOCAL = "local"
    GCP   = "gcp"

ENVIRONMENT = Environment(os.getenv("ENVIRONMENT", "local"))

if ENVIRONMENT == Environment.LOCAL:
    EMBED_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    EMBED_MODEL      = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    LLM_MODEL        = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
    USE_LOCAL_MODELS = True
else:
    EMBED_MODEL      = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
    LLM_MODEL        = os.getenv("ANTHROPIC_LLM_MODEL", "claude-sonnet-4-6")
    USE_LOCAL_MODELS = False

CHUNK_TARGET_TOKENS  = 500
CHUNK_OVERLAP_TOKENS = 50
