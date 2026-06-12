"""Audio extraction from video using FFmpeg."""
import subprocess
import shutil
from pathlib import Path


def extract_audio(video_path: str, audio_path: str) -> str:
    """Extract mono 16 kHz audio from a video file using ffmpeg.

    Returns the output audio path. Raises RuntimeError on failure.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg is not installed or not on PATH. Install it via your package manager."
        )

    Path(audio_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",  # overwrite output
        "-i",
        video_path,
        "-vn",  # no video
        "-ac",
        "1",  # mono
        "-ar",
        "16000",  # 16 kHz — optimal for Whisper
        "-acodec",
        "pcm_s16le",
        audio_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-1000:]}")

    return audio_path
