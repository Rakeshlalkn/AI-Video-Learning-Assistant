"""Video ORM model."""
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from app.db.database import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[str] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(32), default="upload")  # upload | youtube
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | processing | ready | failed
    # Free-form progress string shown to the user, e.g. "Transcribing…",
    # "Summarizing chunk 7/24".
    progress: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Track the current pipeline stage as an integer 0-100 so the UI can
    # render a determinate progress bar.
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="videos")  # noqa: F821
    documents: Mapped[List["Document"]] = relationship(  # noqa: F821
        "Document", back_populates="video", cascade="all, delete-orphan"
    )
