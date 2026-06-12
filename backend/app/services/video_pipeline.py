"""End-to-end video processing pipeline.

Steps:
  1. Extract audio with FFmpeg
  2. Transcribe with Faster-Whisper
  3. Index transcript chunks in ChromaDB
  4. Generate lesson notes with Gemini
  5. Save Document row + Markdown file

Status updates are written to the Video row throughout so the UI can poll.
"""
import logging
import traceback
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.video import Video
from app.models.document import Document
from app.services import audio, transcription, vector_store, gemini


logger = logging.getLogger(__name__)


def _audio_path_for(video: Video) -> str:
    """Pick an audio output path next to the video file."""
    p = Path(video.file_path)
    return str(p.with_suffix(".wav"))


def process_video(db: Session, video_id: int) -> None:
    """Process a single video. Updates the Video row in place.

    Safe to call from a background thread; opens its own DB session.
    """
    from app.db.database import SessionLocal

    session = SessionLocal()
    try:
        video = session.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error("process_video: video %s not found", video_id)
            return

        try:
            video.status = "processing"
            session.commit()

            # 1. Audio extraction
            logger.info("[video %s] extracting audio from %s", video_id, video.file_path)
            audio_path = _audio_path_for(video)
            audio.extract_audio(video.file_path, audio_path)

            # 2. Transcription
            logger.info("[video %s] transcribing audio", video_id)
            transcript = transcription.transcribe_audio(audio_path)
            video.transcript = transcript
            session.commit()

            # 3. Vector indexing
            logger.info("[video %s] indexing transcript chunks", video_id)
            vector_store.index_transcript(video.user_id, video.id, transcript)

            # 4. Lesson notes
            logger.info("[video %s] generating lesson notes", video_id)
            notes_md = gemini.generate_lesson_notes(transcript, video.title)

            # 5. Persist document
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
            video.error_message = None
            session.commit()
            logger.info("[video %s] done", video_id)

        except Exception as exc:  # noqa: BLE001
            logger.exception("Processing failed for video %s", video_id)
            video = session.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = "failed"
                video.error_message = f"{exc}\n{traceback.format_exc()[-1000:]}"
                session.commit()
    finally:
        session.close()
