"""Transcription using faster-whisper (loaded lazily)."""
from functools import lru_cache

from faster_whisper import WhisperModel

from app.core.config import settings


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    """Load and cache the Whisper model (singleton)."""
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_audio(audio_path: str) -> str:
    """Transcribe an audio file to a single transcript string.

    Returns the full transcript with timestamps embedded as inline markers.
    """
    model = get_whisper_model()
    segments, _info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
        word_timestamps=False,
    )

    parts: list[str] = []
    for seg in segments:
        # Format: [HH:MM:SS] text
        start = seg.start or 0.0
        h = int(start // 3600)
        m = int((start % 3600) // 60)
        s = int(start % 60)
        parts.append(f"[{h:02d}:{m:02d}:{s:02d}] {seg.text.strip()}")

    return "\n".join(parts).strip()
