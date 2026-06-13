"""End-to-end video processing pipeline.

Steps:
  1. Extract audio with FFmpeg
  2. Transcribe with Faster-Whisper
  3. Index transcript chunks in ChromaDB
  4. Generate lesson notes with Gemini (map-reduce over chunks for long videos)
  5. Save Document row + Markdown file

Status updates are written to the Video row throughout so the UI can poll.
"""
import logging
import threading
import traceback
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.video import Video
from app.models.document import Document
from app.services import audio, transcription, vector_store, gemini
from app.services.vector_store import estimate_tokens


logger = logging.getLogger(__name__)


def _audio_path_for(video: Video) -> str:
    """Pick an audio output path next to the video file."""
    p = Path(video.file_path)
    return str(p.with_suffix(".wav"))


class _ProgressWriter:
    """Thread-safe progress writer that updates a Video row in a private session.

    `progress()` is called from worker threads (the map step), so it uses a
    lock to serialize session.commit() calls and avoid interleaving writes.
    """

    def __init__(self, video_id: int):
        self.video_id = video_id
        self._lock = threading.Lock()

    def __call__(self, message: str, pct: int) -> None:
        with self._lock:
            from app.db.database import SessionLocal
            session = SessionLocal()
            try:
                v = session.query(Video).filter(Video.id == self.video_id).first()
                if not v:
                    return
                v.progress = message
                v.progress_pct = max(0, min(100, int(pct)))
                session.commit()
            except Exception as exc:  # noqa: BLE001
                logger.debug("progress write failed: %s", exc)
            finally:
                session.close()


def process_video(db: Session, video_id: int) -> None:
    """Process a single video. Updates the Video row in place.

    Safe to call from a background thread; opens its own DB session.
    """
    from app.db.database import SessionLocal

    session = SessionLocal()
    progress = _ProgressWriter(video_id)
    try:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error("process_video: video %s not found", video_id)
            return

        try:
            video.status = "processing"
            video.error_message = None
            video.progress = "Starting…"
            video.progress_pct = 1
            session.commit()

            # 1. Audio extraction --------------------------------------------------
            progress("Extracting audio…", 5)
            logger.info("[video %s] extracting audio from %s", video_id, video.file_path)
            audio_path = _audio_path_for(video)
            audio.extract_audio(video.file_path, audio_path)

            # 2. Transcription ----------------------------------------------------
            progress("Transcribing audio (Whisper)…", 15)
            logger.info("[video %s] transcribing audio", video_id)
            transcript = transcription.transcribe_audio(audio_path)
            video.transcript = transcript
            video.progress = f"Transcribed (≈{estimate_tokens(transcript)} tokens)"
            video.progress_pct = 55
            session.commit()

            # 3. Vector indexing --------------------------------------------------
            progress("Indexing transcript for RAG…", 65)
            logger.info("[video %s] indexing transcript chunks", video_id)
            n_chunks = vector_store.index_transcript(video.user_id, video.id, transcript)
            logger.info("[video %s] indexed %d chunks", video_id, n_chunks)

            # 4. Lesson notes (map-reduce for long transcripts) -------------------
            total_tokens = estimate_tokens(transcript)
            if total_tokens > gemini.DEFAULT_CHUNK_TOKENS:
                progress(
                    f"Generating notes (map-reduce, {total_tokens} tokens)…",
                    70,
                )
            else:
                progress("Generating notes…", 70)
            logger.info("[video %s] generating lesson notes", video_id)

            def notes_progress(message: str, pct: int) -> None:
                # Map step lives in 70–90%, reduce step finishes at 95%.
                progress(message, pct)

            notes_md = gemini.generate_lesson_notes(
                transcript,
                video.title,
                progress_cb=notes_progress,
            )

            # 5. Persist document -------------------------------------------------
            progress("Saving notes…", 95)
            doc = Document(
                video_id=video.id,
                title=f"{video.title} — Lesson Notes",
                content=notes_md,
                doc_type="notes",
            )
            session.add(doc)
            session.commit()

            # 6. Also write a Markdown file to disk
            doc_dir = Path(settings.documents_dir) / str(video.user_id) / str(video.id)
            doc_dir.mkdir(parents=True, exist_ok=True)
            md_path = doc_dir / "notes.md"
            md_path.write_text(notes_md, encoding="utf-8")

            video.status = "ready"
            video.progress = "Ready"
            video.progress_pct = 100
            video.error_message = None
            session.commit()
            logger.info("[video %s] done", video_id)

        except Exception as exc:  # noqa: BLE001
            logger.exception("Processing failed for video %s", video_id)
            video = session.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = "failed"
                video.error_message = f"{exc}\n{traceback.format_exc()[-1000:]}"
                video.progress = "Failed"
                session.commit()
    finally:
        session.close()

