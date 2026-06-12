#!/usr/bin/env bash
# Convenience script to start the backend.
# Usage:  ./run.sh
set -e
cd "$(dirname "$0")"
export PYTHONUNBUFFERED=1
if [ ! -f .env ]; then
  echo "No .env found, copying .env.example. Edit it with your keys before running."
  cp .env.example .env
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
