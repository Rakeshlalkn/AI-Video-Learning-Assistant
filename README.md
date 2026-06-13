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
  3. Chunk + embed transcript → ChromaDB (RAG index for chat)
  4. Generate structured lesson notes with Gemini 2.5 Flash
     — **map-reduce over ~1,100-token chunks** so 2-3 hour videos
     fit comfortably inside Gemini's context window.
  5. Save a Markdown document alongside the video
  6. Live progress bar in the UI (e.g. "Summarizing chunk 7/24…")
- **AI chat tutor** — answers questions, generates quizzes, creates
  flashcards, all grounded in the transcript via RAG.
- **Notes editor** — view, edit, and download notes as Markdown.
- **Dashboard** — totals and recent uploads.
- **Per-user isolation** — every query is scoped to the signed-in user; you
  cannot see or touch another user's videos.

> 📘 Want to understand *why* each piece works the way it does?
> Read [HOW_IT_WORKS.md](HOW_IT_WORKS.md) — it's a full architecture
> walk-through covering auth, the data model, every pipeline step, the
> map-reduce strategy for long videos, configuration, failure modes,
> performance numbers, and how to extend the system.

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
│   ├── Dockerfile          # multi-stage image for the backend
│   ├── requirements.txt
│   ├── .env.example
│   ├── .dockerignore
│   └── run.sh
├── frontend/               # Next.js (App Router) + Tailwind
│   ├── src/app/            # pages: login, dashboard, upload, library, videos/[id], settings
│   ├── src/components/     # Sidebar, NotesEditor, StatusBadge, …
│   ├── src/lib/            # api.ts, auth.tsx, types.ts
│   ├── Dockerfile          # multi-stage image, uses output: "standalone"
│   ├── package.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   ├── .env.example
│   └── .dockerignore
├── docker-compose.yml      # one command to run the whole stack
├── uploads/                # uploaded videos (only used in local-dev mode)
├── documents/              # generated .md notes (only used in local-dev mode)
├── chromadb/               # vector DB persistence (only used in local-dev mode)
├── HOW_IT_WORKS.md         # deep-dive architecture walkthrough
└── README.md
```

## Prerequisites

### If you're using Docker

| Tool | Why | Install |
|------|-----|---------|
| **Docker Engine 24+** with Compose v2 | runs the whole stack | https://docs.docker.com/get-docker/ |
| **Google account** (optional) | real Google Sign-in | https://console.cloud.google.com |

That's it. ffmpeg, Python, and Node are all baked into the images.

### If you're running locally

| Tool | Why | Install |
|------|-----|---------|
| **Python 3.10+** | backend runtime | https://python.org |
| **Node.js 18+** | frontend runtime | https://nodejs.org |
| **ffmpeg** | audio extraction | `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Ubuntu) / `choco install ffmpeg` (Windows) |
| **Google account** (optional) | real Google Sign-in | https://console.cloud.google.com |

> Faster-Whisper will download its model the first time you process a
> video. The default `base` model is ~150 MB. The first run can be slow.

## Setup

You can run the stack two ways. Docker is the path of least resistance if
you have Docker installed; the manual path is useful when you want to
edit Python or Node code without rebuilding images.

### Option A — Docker (recommended)

Prerequisites: Docker Engine 24+ and Docker Compose v2.

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY (required) and SECRET_KEY (recommended).
docker compose up --build
```

That's it. First build takes a few minutes (Whisper + ChromaDB + Next.js).
After that, restarts are near-instant.

You'll get:
- UI at <http://localhost:3000>
- API at <http://localhost:8000> (also <http://localhost:8000/docs>)

Data (SQLite, ChromaDB, uploads, generated .md files, and the Whisper
model cache) is held in a Docker volume called `app_data`. To wipe
everything and start fresh:

```bash
docker compose down -v
```

### Option B — Run locally (no Docker)

#### 1. Backend

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

#### 2. Frontend

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

## How long-video generation works

When a transcript is longer than ~1,100 tokens, the lesson-notes step uses a
**map-reduce** strategy instead of a single prompt:

1. The transcript is split into ~1,100-token chunks (with a 150-token overlap
   so no sentence is cut in half between chunks).  A 2-3 hour lecture
   typically yields 20-30 chunks.
2. **MAP** — Gemini is called once per chunk and asked for a structured
   mini-summary (topics, key facts, examples, important timestamps).
3. **REDUCE** — All chunk summaries + a 20k-char excerpt of the original
   transcript are sent to Gemini in one final call, which produces the
   full structured lesson notes.

Each map step is short enough to run independently and quickly. The reduce
step sees the *whole video's* structure without exceeding the context
window. If a transcript is absurdly long (>60 chunks), chunks are sampled
evenly down to 60 to keep total work bounded.

Chat already uses the same chunked index, so RAG retrieval is just as
accurate on 3-hour videos as on 5-minute ones.



## Troubleshooting

- **"ffmpeg is not installed"** — install ffmpeg and make sure it's on PATH.
  (Not a problem in Docker; ffmpeg is in the image.)
- **"GEMINI_API_KEY is not set"** — set it in `backend/.env` (or the project
  `.env` for Docker) and restart the backend.
- **Whisper is slow** — try `WHISPER_MODEL=tiny` for quick tests; or set
  `WHISPER_DEVICE=cuda` if you have an NVIDIA GPU and the matching
  PyTorch wheel inside the image.
- **CORS errors** — the backend already allows `*` in dev. If you serve the
  frontend on a different port, the `axios` client uses
  `NEXT_PUBLIC_BACKEND_URL` directly, so this should just work.
- **Port already in use** — change the port mapping in `docker-compose.yml`
  (e.g. `"8080:8000"` instead of `"8000:8000"`), or the uvicorn port in
  `run.sh` plus `NEXT_PUBLIC_BACKEND_URL` for local dev.
- **Frontend can't reach backend in Docker** — make sure
  `NEXT_PUBLIC_BACKEND_URL` is set to `http://localhost:8000` *before* you
  build. Public env vars are baked at build time. After changing them,
  rebuild with `docker compose build --no-cache frontend`.
- **HuggingFace model download fails inside Docker** — the cache lives at
  `/data/cache/huggingface` on the `app_data` volume. If your host has
  network restrictions on the Hub, pre-populate the cache by running the
  backend once locally, then `docker compose cp` the cache into the
  volume, or pre-bake it into a derived image.
- **First run is slow** — that's normal. The Whisper model (~150 MB for
  `base`, ~1.5 GB for `small`) and ChromaDB's embedding model (~80 MB)
  download the first time, then live in the `app_data` volume forever.

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
