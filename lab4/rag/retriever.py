"""
lab4/rag/retriever.py

search_docs() — the RAG tool that plugs into registry.py.

This is the only file in the RAG stack that registry.py imports.
It formats retrieved chunks into a prompt-ready string that the model
can reason over.

Prompt format for retrieved context:
    [1] source: getting_started.txt
    Chroma is an open-source vector database designed for AI applications...

    [2] source: architecture.txt
    The retrieval pipeline consists of three stages: embed, search, inject...

The numbered format lets the model cite sources naturally ("according to
document 1...") and helps with provenance tracking.
"""

from __future__ import annotations

from lab4.rag.store import search


# ---------------------------------------------------------------------------
# Morgan's checks
# ---------------------------------------------------------------------------

def _validate_query(query: str) -> str | None:
    """Return error message string if query is invalid, else None."""
    if not isinstance(query, str):
        return f"query must be a string, got {type(query).__name__}"
    if not query.strip():
        return "query cannot be empty"
    if len(query) > 1000:
        return "query too long (max 1000 chars)"
    return None


# ---------------------------------------------------------------------------
# Public tool function
# ---------------------------------------------------------------------------

def search_docs(query: str, limit: int = 3) -> dict:
    """
    Search the internal knowledge base for relevant documents.

    Returns a dict — never raises. Plugs directly into registry.py.

    Args:
        query: Natural language question or search phrase.
        limit: Number of result chunks to return (default 3, clamped to 1-10).

    Returns:
        On success: {"error": False, "query": str, "results": str,
                     "num_results": int}
            where results is a formatted string ready for prompt injection.
        On failure: {"error": True, "message": str}
    """
    # --- Validation ---
    error = _validate_query(query)
    if error:
        return {"error": True, "message": error}

    query = query.strip()
    limit = max(1, min(int(limit) if isinstance(limit, (int, float)) else 3, 10))

    # --- Retrieve ---
    hits = search(query, limit=limit)

    if not hits:
        return {
            "error": False,
            "query": query,
            "results": "No relevant documents found for this query.",
            "num_results": 0,
        }

    # --- Format for prompt injection ---
    formatted = _format_results(hits)

    return {
        "error": False,
        "query": query,
        "results": formatted,
        "num_results": len(hits),
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _format_results(hits: list[dict]) -> str:
    """
    Format search results as a numbered list for prompt injection.

    Each entry includes the source filename for provenance.
    The model is instructed (in the system prompt) to cite these sources.
    """
    lines = []
    for i, hit in enumerate(hits, start=1):
        source = hit.get("source", "unknown")
        text = hit.get("text", "").strip()
        lines.append(f"[{i}] source: {source}\n{text}")

    return "\n\n".join(lines)
