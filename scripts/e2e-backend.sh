#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/apps/backend"

E2E_FRONTEND_ORIGIN="${E2E_FRONTEND_ORIGIN:-http://localhost:3000,http://localhost:3100}"
E2E_BACKEND_PORT="${E2E_BACKEND_PORT:-8000}"
E2E_DATABASE_URL="${E2E_DATABASE_URL:-sqlite:///./e2e-app.db}"

cd "$BACKEND_DIR"

rm -f e2e-app.db
DATABASE_URL="$E2E_DATABASE_URL" uv run alembic upgrade head
DATABASE_URL="$E2E_DATABASE_URL" uv run python scripts/seed_demo.py
DATABASE_URL="$E2E_DATABASE_URL" FRONTEND_ORIGIN="$E2E_FRONTEND_ORIGIN" uv run uvicorn app.main:app --host 127.0.0.1 --port "$E2E_BACKEND_PORT"
