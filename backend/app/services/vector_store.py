"""ChromaDB-backed vector store for transcript chunks.

Each user gets their own collection so data is naturally partitioned.
Embeddings are produced by ChromaDB's default embedding function
(all-MiniLM-L6-v2 sentence-transformer) — no extra API key needed.
"""
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


def chunk_transcript(transcript: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split a transcript into overlapping character chunks.

    Tries to break on sentence/paragraph boundaries when possible.
    """
    if not transcript:
        return []

    # First try splitting on timestamped lines if present
    lines = transcript.split("\n")
    chunks: list[str] = []
    current = ""

    for line in lines:
        if not line.strip():
            continue
        if len(current) + len(line) + 1 <= chunk_size:
            current = (current + "\n" + line).strip() if current else line
        else:
            if current:
                chunks.append(current)
            # If a single line is bigger than chunk_size, hard split
            if len(line) > chunk_size:
                for i in range(0, len(line), chunk_size - overlap):
                    chunks.append(line[i : i + chunk_size])
                current = ""
            else:
                current = line

    if current:
        chunks.append(current)

    return chunks


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
