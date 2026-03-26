"""
lab4/rag/loader.py

Loads plain-text documents from lab4/data/docs/ and indexes them
into the Chroma vector store via store.add_docs().

Run once before starting the chatbot:
    uv run python -m lab4.rag.loader

Riley's chunking strategy:
  - Chunk at paragraph boundaries (double newline), not fixed character count
  - Minimum chunk size: 50 chars (skip whitespace-only or near-empty chunks)
  - Maximum chunk size: 1500 chars (split oversized paragraphs at sentence end)
  - Each chunk carries its source filename as provenance metadata

Why paragraph chunking beats fixed-size:
  Fixed-size chunking (e.g. every 500 chars) splits sentences mid-thought,
  creating chunks where the first sentence has no context. Paragraph chunking
  preserves semantic units — a paragraph is usually about one thing.
  Retrieval accuracy improves 20-40% in practice.
"""

from __future__ import annotations

import re
from pathlib import Path

from lab4.rag.store import add_docs, collection_size


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"
MIN_CHUNK_CHARS = 50
MAX_CHUNK_CHARS = 1500


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def load_and_index(docs_dir: Path = DOCS_DIR, verbose: bool = True) -> int:
    """
    Load all .txt files from docs_dir, chunk them, and index into Chroma.

    Args:
        docs_dir: Directory containing .txt documents.
        verbose:  Print progress if True.

    Returns:
        Total number of chunks indexed.
    """
    txt_files = sorted(docs_dir.glob("*.txt"))

    if not txt_files:
        print(f"[loader] No .txt files found in {docs_dir}")
        print(f"[loader] Create 20 .txt files in {docs_dir} before running.")
        return 0

    if verbose:
        print(f"[loader] Found {len(txt_files)} documents in {docs_dir}")

    all_chunks: list[dict] = []

    for filepath in txt_files:
        chunks = _chunk_file(filepath)
        all_chunks.extend(chunks)
        if verbose:
            print(f"  {filepath.name}: {len(chunks)} chunks")

    if verbose:
        print(f"[loader] Indexing {len(all_chunks)} total chunks...")

    indexed = add_docs(all_chunks)

    if verbose:
        print(f"[loader] Done. Collection size: {collection_size()} chunks.")

    return indexed


# ---------------------------------------------------------------------------
# Internal chunking
# ---------------------------------------------------------------------------

def _chunk_file(filepath: Path) -> list[dict]:
    """
    Read a .txt file and split it into paragraph-boundary chunks.

    Returns a list of chunk dicts ready for store.add_docs().
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"  [loader] Could not read {filepath.name}: {exc}")
        return []

    raw_paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    chunk_index = 0

    for para in raw_paragraphs:
        para = para.strip()
        if len(para) < MIN_CHUNK_CHARS:
            continue

        # Split oversized paragraphs at sentence boundaries
        if len(para) > MAX_CHUNK_CHARS:
            sub_chunks = _split_at_sentences(para)
        else:
            sub_chunks = [para]

        for sub in sub_chunks:
            sub = sub.strip()
            if len(sub) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "text": sub,
                    "source": filepath.name,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

    return chunks


def _split_at_sentences(text: str) -> list[str]:
    """
    Split a long paragraph into sentence-boundary chunks under MAX_CHUNK_CHARS.
    Falls back to hard split if no sentence boundaries are found.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= MAX_CHUNK_CHARS:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            # Sentence itself is too long — hard split
            if len(sentence) > MAX_CHUNK_CHARS:
                for i in range(0, len(sentence), MAX_CHUNK_CHARS):
                    chunks.append(sentence[i : i + MAX_CHUNK_CHARS])
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    total = load_and_index(verbose=True)
    print(f"\n[loader] Indexed {total} chunks total.")
