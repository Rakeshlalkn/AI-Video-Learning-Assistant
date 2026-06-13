# syntax=docker/dockerfile:1.7
#
# FastAPI backend image.
#
# Base: python:3.11-slim. ffmpeg is added here so the audio extractor can run
# inside the container. We pick the "slim" base so the image is small enough
# to download in a reasonable time, and add only the bits we actually need.
#
# We also pre-install build tools briefly to compile numpy / chromadb's
# transitive deps, then purge them at the end of the build to keep the
# final image small. apt's autoremove is your friend.

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# OS deps needed at build time: build-essential + libffi-dev for cffi / bcrypt.
# ffmpeg is also a runtime dep, so we install it now and just keep it.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libffi-dev \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps in a separate layer so source changes don't bust the
# dependency cache on rebuilds.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


# ---------------------------------------------------------------------------
# Final runtime image. We start fresh from the slim base and copy in only
# what we need. This keeps the runtime image ~600 MB smaller than a single
# stage build.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # faster-whisper / CTranslate2: download once, reuse forever
    HF_HOME=/cache/huggingface \
    # uvicorn bind defaults
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000

# We still need ffmpeg at runtime, plus libgomp for CTranslate2.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the installed Python packages from the builder.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Application code is placed at /app/backend so PYTHONPATH=/app works.
COPY . /app/backend
ENV PYTHONPATH=/app

# Persistent storage lives on mounted volumes, not inside the image.
# The dirs are created here so volume mounts land on existing paths.
RUN mkdir -p /data/uploads /data/documents /data/chromadb /data/db /data/cache/huggingface

# Healthcheck — `python -c` is cheaper than curl and doesn't need extra tooling.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" \
        || exit 1

EXPOSE 8000

# uvicorn with one worker is intentional: the pipeline already runs in a
# background thread per request, and Faster-Whisper loads a large model
# into memory at startup. Multiple uvicorn workers would multiply the
# memory cost. If you need real concurrency, scale Whisper out separately.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
