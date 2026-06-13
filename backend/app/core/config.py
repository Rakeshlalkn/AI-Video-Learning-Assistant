"""Application configuration loaded from environment variables.

We deliberately read every path from env vars (with sensible defaults that
work in both `python -m uvicorn` and `docker compose up`):

* Locally: paths default to the on-disk layout the project has always used.
* In Docker: docker-compose.yml passes `UPLOAD_DIR=/data/uploads` etc., and
  Pydantic picks them up.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# /app/backend/app/core/config.py → /app/backend
APP_DIR = Path(__file__).resolve().parent.parent.parent
# /app/backend → /app
PROJECT_ROOT = APP_DIR.parent
# The repo root (one above backend/) — the original layout used this for
# uploads/, documents/, chromadb/ sitting alongside frontend/.
REPO_ROOT = APP_DIR.parent


def _default_data_dir(name: str) -> str:
    """Pick a sensible default for a data directory.

    Priority:
      1. Explicit env var (set by docker-compose for /data/*).
      2. `<repo>/<name>` (the original on-disk layout when running locally).
      3. `/data/<name>` (the Docker-friendly fallback).
    """
    env_name = name.upper()
    if env_name in os.environ:
        return os.environ[env_name]
    repo_path = REPO_ROOT / name
    if repo_path.exists() or env_name not in os.environ:
        # Local dev: keep using repo/<name> as before.
        return str(repo_path)
    return f"/data/{name}"


class Settings(BaseSettings):
    """Application settings loaded from .env file + process env."""

    # Google OAuth
    google_client_id: str = "your-google-client-id.apps.googleusercontent.com"
    google_client_secret: str = "your-google-client-secret"

    # JWT
    secret_key: str = "change-me-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Gemini
    gemini_api_key: str = "your-gemini-api-key"
    gemini_model: str = "gemini-2.5-flash"

    # App
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    database_url: str = f"sqlite:///{APP_DIR / 'app.db'}"
    upload_dir: str = _default_data_dir("uploads")
    documents_dir: str = _default_data_dir("documents")
    chroma_dir: str = _default_data_dir("chromadb")

    # Whisper
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    youtube_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    youtube_cookies_file: str | None = None
    youtube_retries: int = 3

    model_config = SettingsConfigDict(
        env_file=str(APP_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

# Ensure runtime directories exist
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.documents_dir).mkdir(parents=True, exist_ok=True)
Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
# SQLite parent dir needs to exist when DATABASE_URL is file-based.
if settings.database_url.startswith("sqlite:///"):
    db_path = Path(settings.database_url.replace("sqlite:///", "", 1))
    db_path.parent.mkdir(parents=True, exist_ok=True)
