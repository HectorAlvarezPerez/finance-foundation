#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/apps/backend"

DEMO_FRONTEND_ORIGIN="${DEMO_FRONTEND_ORIGIN:-http://localhost:3000,http://localhost:3100}"
DEMO_BACKEND_PORT="${DEMO_BACKEND_PORT:-8100}"

DATABASE_URL='sqlite:///./dev-app.db' FRONTEND_ORIGIN="$DEMO_FRONTEND_ORIGIN" uv run uvicorn app.main:app --host 127.0.0.1 --port "$DEMO_BACKEND_PORT"
