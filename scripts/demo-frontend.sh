#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/apps/frontend"

DEMO_FRONTEND_PORT="${DEMO_FRONTEND_PORT:-3100}"
DEMO_API_BASE_URL="${DEMO_API_BASE_URL:-http://localhost:8100/api/v1}"

NEXT_PUBLIC_API_BASE_URL="$DEMO_API_BASE_URL" npm run start -- --port "$DEMO_FRONTEND_PORT"
