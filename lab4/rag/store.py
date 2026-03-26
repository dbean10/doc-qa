"""
lab4/rag/store.py

Chroma vector store wrapper.

Provides two operations:
    add_docs(chunks)         — index a list of text chunks (run once)
    search(query, limit)     — return top-k relevant chunks for a query

Riley's design decisions:
  - Persistent Chroma client: index survives process restarts
  - Collection name includes embed model — prevents silent model mismatch
  - Metadata stored per chunk: source filename + chunk index for provenance
  - search() returns plain strings — retriever.py formats them for the prompt

Chroma persistence path: ./chroma_db (relative to where chatbot.py runs)
Change CHROMA_PATH to an absolute path in production.
"""

from __future__ import annotations

import os
from typing import Optional

import chromadb
from chromadb.config import Settings

from lab4.rag.embedder import embed, get_model_name


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = f"docs_{get_model_name().replace('-', '_').replace('.', '_')}"


# ---------------------------------------------------------------------------
# Client + collection (module-level singleton — one connection per process)
# ---------------------------------------------------------------------------

_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None


def _get_collection() -> chromadb.Collection:
    """Lazy-initialise the Chroma client and collection."""
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},   # cosine similarity
        )
    return _collection


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def add_docs(chunks: list[dict]) -> int:
    """
    Index a list of text chunks into the vector store.

    Each chunk dict must have:
        "text":   str  — the chunk content
        "source": str  — filename or identifier for provenance

    Optional:
        "chunk_index": int — position within the source document

    Args:
        chunks: List of chunk dicts.

    Returns:
        Number of chunks successfully indexed.

    Riley's note: this is idempotent — Chroma upserts by ID so re-running
    loader.py will update existing chunks rather than duplicate them.
    """
    if not chunks:
        return 0

    collection = _get_collection()
    indexed = 0

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if not text:
            continue

        source = chunk.get("source", "unknown")
        chunk_index = chunk.get("chunk_index", 0)

        # Stable, deterministic ID — prevents duplicates on re-index
        doc_id = f"{source}::chunk_{chunk_index}"

        try:
            vector = embed(text)
            collection.upsert(
                ids=[doc_id],
                embeddings=[vector],
                documents=[text],
                metadatas=[{"source": source, "chunk_index": chunk_index}],
            )
            indexed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [store] Failed to index {doc_id}: {exc}")

    return indexed


def search(query: str, limit: int = 3) -> list[dict]:
    """
    Find the top-k chunks most semantically similar to query.

    Args:
        query: Natural language search query.
        limit: Number of results to return (default 3, max 10).

    Returns:
        List of result dicts, each containing:
            "text":        str   — chunk content
            "source":      str   — source filename
            "chunk_index": int   — position in source
            "distance":    float — cosine distance (lower = more similar)

    Returns [] if the collection is empty or query embedding fails.
    """
    limit = max(1, min(limit, 10))  # clamp to [1, 10]

    collection = _get_collection()

    if collection.count() == 0:
        return []

    try:
        query_vector = embed(query)
    except Exception as exc:  # noqa: BLE001
        print(f"  [store] Failed to embed query: {exc}")
        return []

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(limit, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "text": text,
            "source": meta.get("source", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "distance": round(dist, 4),
        })

    return output


def collection_size() -> int:
    """Return the number of indexed chunks. Used by loader.py and tests."""
    return _get_collection().count()


def reset_collection() -> None:
    """
    Delete and recreate the collection. Used in tests to start clean.
    WARNING: destroys all indexed data.
    """
    global _collection
    if _client is not None:
        _client.delete_collection(COLLECTION_NAME)
        _collection = None
