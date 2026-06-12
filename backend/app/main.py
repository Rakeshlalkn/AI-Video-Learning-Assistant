"""FastAPI application entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, dashboard, documents, videos
from app.db.database import init_db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="AI Video Learning Assistant",
    version="0.1.0",
    description="Convert videos into structured learning materials using Gemini + Whisper + ChromaDB.",
)

# CORS — wide open for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Initializing database…")
    init_db()
    logger.info("Database ready.")


@app.get("/health")
def health():
    return {"status": "ok"}


# Mount routers
app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(dashboard.router)
