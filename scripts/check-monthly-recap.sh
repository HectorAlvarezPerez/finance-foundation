#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
USER_ID="${USER_ID:-d5579662-24f8-40fa-b4a0-47b4394e10af}"
SESSION_COOKIE="${SESSION_COOKIE:-eyJ1c2VyX2lkIjoiZDU1Nzk2NjItMjRmOC00MGZhLWI0YTAtNDdiNDM5NGUxMGFmIn0.i4kjEM5b3AmD84xAx0SnjeOyIs4}"
MONTH_KEY="${MONTH_KEY:-$(date +%Y-%m)}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "❌ Falta comando requerido: $1"
    exit 1
  }
}

require_cmd curl
require_cmd jq

if [[ -z "$USER_ID" && -z "$SESSION_COOKIE" ]]; then
  echo "❌ Define USER_ID o SESSION_COOKIE para autenticar"
  echo "   Ejemplo: USER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx scripts/check-monthly-recap.sh"
  exit 1
fi

if [[ "$USER_ID" == "TU_UUID" ]]; then
  echo "❌ USER_ID no puede ser TU_UUID (placeholder)"
  exit 1
fi

AUTH_ARGS=()
if [[ -n "$SESSION_COOKIE" ]]; then
  AUTH_ARGS=(-H "Cookie: finance_foundation_session=$SESSION_COOKIE")
else
  AUTH_ARGS=(-H "X-User-Id: $USER_ID")
fi

api_get() {
  local path="$1"
  curl -sS "${AUTH_ARGS[@]}" "$BASE_URL$path"
}

api_post_json() {
  local path="$1"
  local payload="$2"
  curl -sS -X POST "$BASE_URL$path" \
    -H "Content-Type: application/json" \
    "${AUTH_ARGS[@]}" \
    -d "$payload"
}

echo "➡️  BASE_URL=$BASE_URL"
echo "➡️  MONTH_KEY objetivo=$MONTH_KEY"

summary_json="$(api_get "/api/v1/insights/summary")"
months_count="$(echo "$summary_json" | jq -r '.available_recap_months | length // 0')"

if [[ "$months_count" -eq 0 ]]; then
  echo "❌ No hay meses disponibles en /api/v1/insights/summary"
  echo "   Este script no crea datos automáticamente."
  exit 1
fi

selected_month_key="$(echo "$summary_json" | jq -r --arg mk "$MONTH_KEY" '([.available_recap_months[].month_key] | if index($mk) then $mk else .[0] end) // empty')"

if [[ -z "$selected_month_key" ]]; then
  echo "❌ No se pudo seleccionar month_key desde available_recap_months"
  echo "$summary_json" | jq .
  exit 1
fi

echo "➡️  month_key a probar=$selected_month_key"

regen_json="$(api_post_json "/api/v1/insights/monthly-recap/regenerate" "{\"month_key\":\"$selected_month_key\"}")"
echo "🔁 regenerate:"
echo "$regen_json" | jq '{status, month_key, is_stale, story_ids: [.stories[].id]}'

get_json="$(api_get "/api/v1/insights/monthly-recap?month_key=$selected_month_key")"
echo "📖 get:"
echo "$get_json" | jq '{status, month_key, is_stale, story_ids: [.stories[].id]}'

missing_ids="$(echo "$get_json" | jq -c '(["top-category","biggest-moment","month-comparison"] - ([.stories[].id]))')"
stories_count="$(echo "$get_json" | jq '.stories | length')"
status_value="$(echo "$get_json" | jq -r '.status // "unknown"')"

if [[ "$stories_count" -eq 3 && "$missing_ids" == "[]" ]]; then
  echo "✅ PASS: 3 stories esperadas presentes"
else
  echo "❌ FAIL: stories incompletas. missing=$missing_ids count=$stories_count"
  exit 1
fi

if [[ "$status_value" == "ready" ]]; then
  echo "✅ IA válida (status=ready)"
else
  echo "⚠️  fallback activo (status=$status_value)"
  echo "   Revisa observabilidad: invalid_reason=llm_empty_stories o llm_story_ids_mismatch"
fi
