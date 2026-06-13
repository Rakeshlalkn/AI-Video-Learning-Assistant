"""ChromaDB-backed vector store for transcript chunks.

Each user gets their own collection so data is naturally partitioned.
Embeddings are produced by ChromaDB's default embedding function
(all-MiniLM-L6-v2 sentence-transformer) — no extra API key needed.
"""
from __future__ import annotations

import re
from typing import Iterable

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    """Lazy singleton ChromaDB client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
        )
    return _client


def _collection_name(user_id: str, video_id: int) -> str:
    """Stable, sanitized collection name."""
    safe_user = re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)[:64]
    return f"user_{safe_user}_video_{video_id}"


# ---------------------------------------------------------------------------
# Token-aware chunking
# ---------------------------------------------------------------------------
#
# We don't pull in tiktoken just to measure chunk sizes. The mapping is good
# enough for sizing purposes:
#
#   1 token ≈ 0.75 words (English)  →  1 word ≈ 1.33 tokens
#
# So "1000 tokens" maps to ~750 words, and "1500 tokens" maps to ~1100 words.
# We default to the middle of the requested range (≈1100 tokens, ~825 words).
#
# We keep the *overlap* in characters for the final tail-extension, but the
# primary sizing is word-based.

WORDS_PER_TOKEN = 1.0 / 1.33  # words per token


def _words_to_chars(words: int, sample: str) -> int:
    """Estimate how many characters `words` words are, using the transcript's own density."""
    if not sample:
        return words * 5
    non_ws = sum(1 for c in sample if not c.isspace())
    avg_word_len = max(1.0, non_ws / max(1, len(sample.split())))
    # one word ≈ avg_word_len chars + one space
    return int(words * (avg_word_len + 1))


def chunk_transcript(
    transcript: str,
    chunk_tokens: int = 1100,
    overlap_tokens: int = 150,
) -> list[str]:
    """Split a transcript into overlapping chunks sized to ~`chunk_tokens` tokens.

    Strategy:
      * Treat each timestamped line as an atomic unit so we never split mid-line.
      * Greedily pack lines into a chunk until the target word-count is reached.
      * If a chunk would exceed the target, close it and start a new one with
        an overlap of the last `overlap_tokens` words from the previous chunk.
      * If a single line is itself larger than the target, hard-split it on
        word boundaries.

    A 2-3 hour lecture (≈20k-30k words) yields roughly 20-30 chunks of this
    size, each well within Gemini's context window with room for the prompt.
    """
    if not transcript:
        return []

    target_words = max(50, int(chunk_tokens * WORDS_PER_TOKEN))
    overlap_words = max(0, int(overlap_tokens * WORDS_PER_TOKEN))

    lines = [ln for ln in transcript.split("\n") if ln.strip()]

    def line_words(ln: str) -> int:
        return len(ln.split())

    chunks: list[str] = []
    current_lines: list[str] = []
    current_words = 0
    overlap_buffer: list[str] = []

    def flush():
        nonlocal current_lines, current_words
        if current_lines:
            chunks.append("\n".join(current_lines).strip())
        # keep the tail as overlap for the next chunk
        if overlap_words > 0:
            tail: list[str] = []
            tail_words = 0
            for ln in reversed(current_lines):
                w = line_words(ln)
                if tail_words + w > overlap_words and tail:
                    break
                tail.insert(0, ln)
                tail_words += w
            overlap_buffer[:] = tail
        else:
            overlap_buffer.clear()
        current_lines = []
        current_words = 0

    for line in lines:
        w = line_words(line)

        # If a single line is bigger than the whole budget, hard-split it.
        if w > target_words:
            flush()
            words = line.split()
            step = max(1, target_words - overlap_words)
            for i in range(0, len(words), step):
                piece = " ".join(words[i : i + target_words])
                if piece:
                    chunks.append(piece)
            overlap_buffer.clear()
            continue

        # Start a new chunk if adding this line would exceed the target and we
        # already have content.
        if current_words + w > target_words and current_lines:
            flush()

        # Seed the new chunk with the overlap tail from the previous one.
        if not current_lines and overlap_buffer:
            current_lines = list(overlap_buffer)
            current_words = sum(line_words(ln) for ln in current_lines)

        current_lines.append(line)
        current_words += w

    flush()
    # Drop empty chunks
    return [c for c in chunks if c.strip()]


def estimate_tokens(text: str) -> int:
    """Rough token count for diagnostics."""
    return int(len(text.split()) * 1.33)


def index_transcript(user_id: str, video_id: int, transcript: str) -> int:
    """Chunk the transcript and store it in ChromaDB.

    Returns the number of chunks indexed.
    """
    chunks = chunk_transcript(transcript)
    if not chunks:
        return 0

    client = get_client()
    name = _collection_name(user_id, video_id)
    # delete if exists (idempotent reindex)
    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(
        name=name,
        metadata={"user_id": user_id, "video_id": video_id},
    )

    collection.add(
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))],
    )
    return len(chunks)


def query_transcript(user_id: str, video_id: int, question: str, n_results: int = 5) -> list[str]:
    """Retrieve the top-N relevant transcript chunks for a question."""
    client = get_client()
    name = _collection_name(user_id, video_id)
    try:
        collection = client.get_collection(name)
    except Exception:
        return []

    result = collection.query(query_texts=[question], n_results=n_results)
    docs: list[str] = result.get("documents", [[]])[0]
    return list(docs)


def delete_video_index(user_id: str, video_id: int) -> None:
    """Remove a video's collection from ChromaDB."""
    client = get_client()
    name = _collection_name(user_id, video_id)
    try:
        client.delete_collection(name)
    except Exception:
        pass
