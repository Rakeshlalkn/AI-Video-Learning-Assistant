"""Document CRUD endpoints (notes editor + download)."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.document import Document
from app.models.user import User
from app.models.video import Video
from app.schemas.video import DocumentOut, DocumentUpdate


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(
    video_id: int | None = None,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents owned by the user. Optionally filter by video_id."""
    q = (
        db.query(Document)
        .join(Video, Document.video_id == Video.id)
        .filter(Video.user_id == current.id)
    )
    if video_id is not None:
        q = q.filter(Document.video_id == video_id)
    return q.order_by(Document.created_at.desc()).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = _get_owned_doc(db, current, doc_id)
    return doc


@router.put("/{doc_id}", response_model=DocumentOut)
def update_document(
    doc_id: int,
    body: DocumentUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update document content (notes editor)."""
    doc = _get_owned_doc(db, current, doc_id)
    doc.content = body.content
    db.commit()
    db.refresh(doc)

    # Keep the on-disk Markdown in sync
    try:
        video = db.query(Video).filter(Video.id == doc.video_id).first()
        if video:
            md_path = Path(settings.documents_dir) / str(video.user_id) / str(video.id) / "notes.md"
            md_path.write_text(doc.content, encoding="utf-8")
    except Exception:
        pass

    return doc


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a document as a Markdown file."""
    doc = _get_owned_doc(db, current, doc_id)
    safe_title = "".join(c if c.isalnum() or c in "-_." else "_" for c in doc.title) or "document"
    user_dir = Path(settings.documents_dir) / current.id / "_downloads"
    user_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = user_dir / f"{doc.id}_{safe_title}.md"
    tmp_path.write_text(doc.content, encoding="utf-8")
    return FileResponse(
        path=str(tmp_path),
        media_type="text/markdown",
        filename=f"{safe_title}.md",
    )


def _get_owned_doc(db: Session, user: User, doc_id: int) -> Document:
    """Return a Document if it belongs to the user, else 404."""
    doc = (
        db.query(Document)
        .join(Video, Document.video_id == Video.id)
        .filter(Document.id == doc_id, Video.user_id == user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
