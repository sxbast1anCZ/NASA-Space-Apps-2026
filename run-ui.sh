#!/usr/bin/env bash
# Local UI prototype: API on :8000 and the web app on :5173. Ctrl+C stops both.
cd "$(dirname "$0")"
.venv/bin/uvicorn backend.ui:app --port 8000 &
API=$!
trap 'kill $API' EXIT
npm --prefix frontend run dev -- --port 5173
