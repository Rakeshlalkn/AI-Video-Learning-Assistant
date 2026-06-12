"""Application configuration loaded from environment variables."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

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
    database_url: str = f"sqlite:///{BASE_DIR / 'app.db'}"
    upload_dir: str = str(BASE_DIR.parent / "uploads")
    documents_dir: str = str(BASE_DIR.parent / "documents")
    chroma_dir: str = str(BASE_DIR.parent / "chromadb")

    # Whisper
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

# Ensure runtime directories exist
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.documents_dir).mkdir(parents=True, exist_ok=True)
Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
