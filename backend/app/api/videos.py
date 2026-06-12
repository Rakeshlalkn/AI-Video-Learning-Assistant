"""Video upload, listing, processing, and YouTube import endpoints."""
import logging
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.video import Video
from app.models.document import Document
from app.schemas.video import (
    DocumentOut,
    VideoOut,
    VideoSummary,
    YouTubeImportRequest,
)
from app.services import youtube
from app.services.video_pipeline import process_video


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/videos", tags=["videos"])


ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB


def _safe_filename(name: str) -> str:
    """Make a filename safe-ish: keep extension, replace problematic chars."""
    p = Path(name)
    ext = p.suffix.lower()
    stem = "".join(c if c.isalnum() or c in "-_." else "_" for c in p.stem)
    return f"{stem}{ext}"


@router.post("/upload", response_model=VideoOut)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a video file and queue it for processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    user_dir = Path(settings.upload_dir) / current.id
    user_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    dest_path = user_dir / unique_name

    # Stream to disk to avoid loading huge files in memory
    size = 0
    with dest_path.open("wb") as out:
        while chunk := file.file.read(8 * 1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                dest_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large (max 2 GB)")
            out.write(chunk)

    video = Video(
        user_id=current.id,
        title=title or Path(file.filename).stem,
        file_path=str(dest_path),
        source_type="upload",
        status="pending",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # Process in a background thread (FastAPI BackgroundTasks runs after response)
    background_tasks.add_task(_run_in_thread, video.id)
    return video


@router.post("/youtube", response_model=VideoOut)
def import_youtube(
    body: YouTubeImportRequest,
    background_tasks: BackgroundTasks,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a YouTube video and queue it for processing."""
    if not youtube.is_youtube_url(body.url):
        raise HTTPException(status_code=400, detail="Not a valid YouTube URL")

    try:
        file_path, yt_title = youtube.download_youtube(body.url, str(Path(settings.upload_dir) / current.id))
    except Exception as exc:  # noqa: BLE001
        logger.exception("YouTube download failed")
        raise HTTPException(status_code=400, detail=f"YouTube download failed: {exc}")

    video = Video(
        user_id=current.id,
        title=body.title or yt_title,
        file_path=file_path,
        source_type="youtube",
        source_url=body.url,
        status="pending",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    background_tasks.add_task(_run_in_thread, video.id)
    return video


@router.post("/{video_id}/process", response_model=VideoOut)
def trigger_process(
    video_id: int,
    background_tasks: BackgroundTasks,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-trigger processing for a video (e.g. after a failure)."""
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video.status = "pending"
    video.error_message = None
    db.commit()
    db.refresh(video)

    background_tasks.add_task(_run_in_thread, video.id)
    return video


@router.get("", response_model=list[VideoSummary])
def list_videos(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's videos, newest first."""
    rows = (
        db.query(Video)
        .filter(Video.user_id == current.id)
        .order_by(desc(Video.created_at))
        .all()
    )
    return rows


@router.get("/{video_id}", response_model=VideoOut)
def get_video(
    video_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single video with its transcript."""
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.delete("/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a video, its files, its notes, and its vector index."""
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Delete local files
    try:
        Path(video.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    audio_path = Path(video.file_path).with_suffix(".wav")
    audio_path.unlink(missing_ok=True)

    # Delete ChromaDB collection
    from app.services import vector_store
    vector_store.delete_video_index(current.id, video.id)

    # Cascade deletes documents via ORM relationship
    db.delete(video)
    db.commit()
    return None


@router.get("/{video_id}/documents", response_model=list[DocumentOut])
def list_documents(
    video_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents (notes) for a video."""
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return (
        db.query(Document)
        .filter(Document.video_id == video_id)
        .order_by(Document.created_at.asc())
        .all()
    )


def _run_in_thread(video_id: int) -> None:
    """Spawn a daemon thread for the (potentially long) pipeline."""
    t = threading.Thread(target=process_video, args=(None, video_id), daemon=True)
    t.start()
