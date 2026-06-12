"""Pydantic schemas — videos and documents."""
from datetime import datetime
from pydantic import BaseModel


class VideoBase(BaseModel):
    title: str
    source_type: str = "upload"
    source_url: str | None = None


class VideoCreate(VideoBase):
    pass


class YouTubeImportRequest(BaseModel):
    url: str
    title: str | None = None


class VideoOut(BaseModel):
    id: int
    user_id: str
    title: str
    file_path: str
    source_type: str
    source_url: str | None = None
    transcript: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class VideoSummary(BaseModel):
    id: int
    title: str
    status: str
    source_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    video_id: int
    title: str
    content: str
    doc_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    content: str


class ChatRequest(BaseModel):
    video_id: int
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
