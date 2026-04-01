#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/apps/backend"
DEMO_API_BASE_URL="${DEMO_API_BASE_URL:-http://localhost:8100/api/v1}"

cd "$BACKEND_DIR"

rm -f dev-app.db
DATABASE_URL='sqlite:///./dev-app.db' uv run alembic upgrade head
DATABASE_URL='sqlite:///./dev-app.db' uv run python scripts/seed_demo.py

cd "$ROOT_DIR"
NEXT_PUBLIC_API_BASE_URL="$DEMO_API_BASE_URL" npm run build:frontend
