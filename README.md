# AI Video Learning Assistant

Turn any video — local file or YouTube URL — into a structured lesson with
transcript, AI-generated notes, and a chat tutor that answers questions
grounded in the video.

Built as a fully local stack. **No AWS, no Kubernetes, no paid infra.** All
data stays on your machine: SQLite for metadata, ChromaDB for vectors, plain
folders for video and Markdown files.

```
┌──────────────────────────┐         ┌──────────────────────────┐
│  Next.js + Tailwind UI   │  HTTP   │      FastAPI backend     │
│  (frontend/)             │ ──────► │      (backend/)          │
│  Google Sign-in          │         │  Google OAuth · JWT      │
└──────────────────────────┘         │  ffmpeg audio extract    │
                                     │  Faster-Whisper          │
                                     │  Gemini 2.5 Flash        │
                                     │  ChromaDB RAG            │
                                     │  SQLite (metadata)       │
                                     └──────────────────────────┘
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       ▼                        ▼                        ▼
                uploads/                  documents/                chromadb/
                (videos)                  (.md notes)            (vector index)
```

## Features

- **Google Sign-in** (with a built-in dev-mode login so you can try the app
  without setting up OAuth).
- **Video upload** — MP4, MKV, MOV, AVI, WEBM.
- **YouTube URL import** — video is downloaded locally with `yt-dlp`, then
  processed the same way as uploaded files.
- **Automatic pipeline**
  1. Extract audio with `ffmpeg`
  2. Transcribe with Faster-Whisper (local, runs on CPU)
  3. Chunk + embed transcript → ChromaDB
  4. Generate structured lesson notes with Gemini 2.5 Flash
  5. Save a Markdown document alongside the video
- **AI chat tutor** — answers questions, generates quizzes, creates
  flashcards, all grounded in the transcript via RAG.
- **Notes editor** — view, edit, and download notes as Markdown.
- **Dashboard** — totals and recent uploads.
- **Per-user isolation** — every query is scoped to the signed-in user; you
  cannot see or touch another user's videos.

## Folder structure

```
ai-video-learning-assistant/
├── backend/                # FastAPI app
│   ├── app/
│   │   ├── api/            # route handlers
│   │   ├── core/           # config, security
│   │   ├── db/             # SQLAlchemy session + Base
│   │   ├── models/         # ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # audio, transcription, vector store, gemini, pipeline
│   │   └── main.py
│   ├── requirements.txt
│   ├── .env.example
│   └── run.sh
├── frontend/               # Next.js (App Router) + Tailwind
│   ├── src/app/            # pages: login, dashboard, upload, library, videos/[id], settings
│   ├── src/components/     # Sidebar, NotesEditor, StatusBadge, …
│   ├── src/lib/            # api.ts, auth.tsx, types.ts
│   ├── package.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   └── .env.example
├── uploads/                # uploaded videos (created at runtime)
├── documents/              # generated .md notes (created at runtime)
├── chromadb/               # vector DB persistence (created at runtime)
└── README.md
```

## Prerequisites

Install these once on your machine:

| Tool | Why | Install |
|------|-----|---------|
| **Python 3.10+** | backend runtime | https://python.org |
| **Node.js 18+** | frontend runtime | https://nodejs.org |
| **ffmpeg** | audio extraction | `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Ubuntu) / `choco install ffmpeg` (Windows) |
| **Google account** (optional) | real Google Sign-in | https://console.cloud.google.com |

> Faster-Whisper will download its model the first time you process a
> video. The default `base` model is ~150 MB. The first run can be slow.

## Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env:
#   - GEMINI_API_KEY=…         (required for processing & chat)
#   - GOOGLE_CLIENT_ID=…       (optional, enables real Google login)
#   - GOOGLE_CLIENT_SECRET=…   (optional)
./run.sh
```

The API will be at <http://localhost:8000>. Swagger docs at
<http://localhost:8000/docs>.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local if you have a real Google client id.
npm run dev
```

The UI will be at <http://localhost:3000>.

## First run

1. Open <http://localhost:3000>.
2. If you haven't set `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, the login page will
   show a **dev-mode** form — type any name/email and click *Sign in as
   dev user*. A JWT is created locally and the user is upserted in the
   backend.
3. Click **Upload Video** and pick any short MP4 (or paste a YouTube
   URL). Status will move from `pending` → `processing` → `ready`.
4. Open the video to see the **Notes** tab (edit + download) and the
   **Transcript** tab.
5. Use the **Chat** button to ask questions like "summarize the lesson",
   "explain chapter 3", "generate 5 quiz questions".

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/google` | Verify a Google id_token, return JWT + user |
| `GET`  | `/auth/me` | Current user (requires Bearer token) |
| `POST` | `/videos/upload` | Multipart upload of a video file |
| `POST` | `/videos/youtube` | Body: `{ url, title? }` — download & queue |
| `POST` | `/videos/{id}/process` | Re-trigger processing (e.g. after a failure) |
| `GET`  | `/videos` | List the user's videos |
| `GET`  | `/videos/{id}` | Get one video (with transcript when ready) |
| `DELETE` | `/videos/{id}` | Delete a video, its files, its notes, its vector index |
| `GET`  | `/videos/{id}/documents` | List documents for a video |
| `POST` | `/chat` | Body: `{ video_id, question }` → RAG answer |
| `GET`  | `/documents` | List all docs (optionally `?video_id=`) |
| `GET`  | `/documents/{id}` | Get one document |
| `PUT`  | `/documents/{id}` | Body: `{ content }` — save edits |
| `GET`  | `/documents/{id}/download` | Download as `.md` |
| `GET`  | `/dashboard` | Totals + recent uploads |
| `GET`  | `/health` | Liveness check |

All endpoints except `/auth/google`, `/health`, and `/docs` require
`Authorization: Bearer <jwt>`.

## Database schema

```
users      (id PK, name, email, profile_image, created_at)
videos     (id PK, user_id FK, title, file_path, source_type, source_url,
            transcript, status, error_message, created_at)
documents  (id PK, video_id FK, title, content, doc_type, created_at, updated_at)
```

`status` is one of `pending | processing | ready | failed`.
`source_type` is one of `upload | youtube`.

## Configuration cheatsheet

`backend/.env` keys (all optional except `GEMINI_API_KEY`):

```
GOOGLE_CLIENT_ID=…                    # optional — enables real Google login
GOOGLE_CLIENT_SECRET=…
SECRET_KEY=…                          # JWT signing key
GEMINI_API_KEY=…                      # required
GEMINI_MODEL=gemini-2.5-flash
WHISPER_MODEL=base                    # tiny | base | small | medium | large-v3
WHISPER_DEVICE=cpu                    # or cuda
WHISPER_COMPUTE_TYPE=int8             # int8 | float16 | float32
UPLOAD_DIR=../uploads
DOCUMENTS_DIR=../documents
CHROMA_DIR=../chromadb
```

## Troubleshooting

- **"ffmpeg is not installed"** — install ffmpeg and make sure it's on PATH.
- **"GEMINI_API_KEY is not set"** — set it in `backend/.env` and restart the
  backend.
- **Whisper is slow** — try `WHISPER_MODEL=tiny` for quick tests; or set
  `WHISPER_DEVICE=cuda` if you have an NVIDIA GPU.
- **CORS errors** — the backend already allows `*` in dev. If you serve the
  frontend on a different port, the `axios` client uses
  `NEXT_PUBLIC_BACKEND_URL` directly, so this should just work.
- **Port already in use** — change the uvicorn port in `run.sh` and the
  `NEXT_PUBLIC_BACKEND_URL` env var.

## What you can build next

The codebase is structured to make these easy:

- **Quiz Generation** — add a button that calls a Gemini prompt with the
  transcript and the document's quiz section.
- **PDF Export** — call `weasyprint` or `pandoc` on the saved Markdown.
- **Flashcards** — small new schema + a UI tab that asks Gemini to emit
  `Q: … / A: …` pairs in JSON.
- **Multi-video Course Creation** — a `courses` table referencing many
  `videos`, and a RAG index per course.
- **AI Tutor Mode** — turn the chat endpoint into a multi-step "plan →
  ask → quiz → review" loop.

Enjoy! 🎓
