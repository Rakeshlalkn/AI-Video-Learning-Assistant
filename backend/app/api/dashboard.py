"""Dashboard summary endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.video import Video
from app.models.document import Document
from app.schemas.video import VideoSummary


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate counts and recent uploads for the dashboard."""
    total_videos = db.query(func.count(Video.id)).filter(Video.user_id == current.id).scalar() or 0
    total_documents = (
        db.query(func.count(Document.id))
        .join(Video, Document.video_id == Video.id)
        .filter(Video.user_id == current.id)
        .scalar()
        or 0
    )
    ready_videos = (
        db.query(func.count(Video.id))
        .filter(Video.user_id == current.id, Video.status == "ready")
        .scalar()
        or 0
    )

    recent = (
        db.query(Video)
        .filter(Video.user_id == current.id)
        .order_by(Video.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_videos": total_videos,
        "total_documents": total_documents,
        "ready_videos": ready_videos,
        "recent": [VideoSummary.model_validate(v) for v in recent],
    }
