#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/apps/backend"

DEV_FRONTEND_ORIGIN="${DEV_FRONTEND_ORIGIN:-http://localhost:3000,http://localhost:3100}"
DEV_BACKEND_PORT="${DEV_BACKEND_PORT:-8000}"
DEV_DATABASE_URL="${DEV_DATABASE_URL:-sqlite:///./dev-app.db}"

DATABASE_URL="$DEV_DATABASE_URL" uv run alembic upgrade head
DATABASE_URL="$DEV_DATABASE_URL" FRONTEND_ORIGIN="$DEV_FRONTEND_ORIGIN" uv run uvicorn app.main:app --reload --host 127.0.0.1 --port "$DEV_BACKEND_PORT"
