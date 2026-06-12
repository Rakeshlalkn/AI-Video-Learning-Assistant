"""AI chat endpoint — RAG over transcript chunks."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.video import Video
from app.schemas.video import ChatRequest, ChatResponse
from app.services import gemini, vector_store


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Answer a question about a video using RAG."""
    video = (
        db.query(Video)
        .filter(Video.id == body.video_id, Video.user_id == current.id)
        .first()
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Video is not ready for chat (status: {video.status})",
        )

    chunks = vector_store.query_transcript(current.id, video.id, body.question, n_results=5)
    answer = gemini.chat_with_context(body.question, chunks)
    return ChatResponse(answer=answer, sources=chunks)
