"""YouTube download via yt-dlp."""
import re
from pathlib import Path

import yt_dlp


YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+"
)


def is_youtube_url(url: str) -> bool:
    """Return True if the URL looks like a YouTube link."""
    return bool(YOUTUBE_URL_RE.search(url))


def download_youtube(url: str, output_dir: str) -> tuple[str, str]:
    """Download a YouTube video as mp4 (best video+audio merged, height<=720).

    Returns (file_path, title).
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    outtmpl = str(Path(output_dir) / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        # If merge_output_format changed the extension, fix it
        if not Path(file_path).exists():
            base = Path(file_path).with_suffix("")
            for cand in [base.with_suffix(".mp4"), base.with_suffix(".mkv")]:
                if cand.exists():
                    file_path = str(cand)
                    break
        title = info.get("title", "YouTube Video")

    return file_path, title
