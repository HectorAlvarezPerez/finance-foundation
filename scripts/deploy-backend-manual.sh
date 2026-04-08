#!/usr/bin/env bash
set -euo pipefail

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

get_containerapp_image() {
  local app_name="$1"
  local image

  image="$(
    az containerapp show \
      --name "$app_name" \
      --resource-group "$AZURE_RESOURCE_GROUP" \
      --query properties.template.containers[0].image \
      --output tsv \
      2>/dev/null || true
  )"

  if [ "$image" = "null" ]; then
    image=""
  fi

  printf '%s' "$image"
}

notify_deploy() {
  local service="$1"
  local environment="$2"
  local image="$3"
  local url="$4"
  local commit_sha="$5"
  local previous_image="$6"
  local args=(
    --service "$service"
    --environment "$environment"
    --image "$image"
    --url "$url"
    --commit-sha "$commit_sha"
  )

  if ! command -v python3 >/dev/null 2>&1; then
    echo "Skipping Slack notification: python3 is not available." >&2
    return 0
  fi

  if [ -n "$previous_image" ]; then
    args+=(--previous-image "$previous_image")
  fi

  if command -v uv >/dev/null 2>&1; then
    if uv run --with "langfuse>=3.0.0" python3 scripts/deploy/notify.py "${args[@]}"; then
      return 0
    fi
  fi

  python3 scripts/deploy/notify.py "${args[@]}" || true
}

require_cmd az

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finance-foundation-rg}"
AZURE_CONTAINER_REGISTRY_NAME="${AZURE_CONTAINER_REGISTRY_NAME:-financefoundationacr}"
AZURE_BACKEND_CONTAINER_APP_NAME="${AZURE_BACKEND_CONTAINER_APP_NAME:-finance-foundation-backend}"
BACKEND_IMAGE_NAME="${BACKEND_IMAGE_NAME:-finance-foundation-backend}"
IMAGE_TAG_SUFFIX="${IMAGE_TAG_SUFFIX:-manual-$(date +%Y%m%d%H%M%S)}"
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="${AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT:-}"
AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID="${AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID:-prebuilt-layout}"
AZURE_DOCUMENT_INTELLIGENCE_API_KEY="${AZURE_DOCUMENT_INTELLIGENCE_API_KEY:-}"
AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-}"
AZURE_OPENAI_PDF_PARSER_DEPLOYMENT="${AZURE_OPENAI_PDF_PARSER_DEPLOYMENT:-}"
AZURE_OPENAI_TRANSACTION_CATEGORY_DEPLOYMENT="${AZURE_OPENAI_TRANSACTION_CATEGORY_DEPLOYMENT:-}"
AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT="${AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT:-${AZURE_OPENAI_TRANSACTION_CATEGORY_DEPLOYMENT:-}}"
AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION:-2025-03-01-preview}"
AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY:-}"
LANGFUSE_ENABLED="${LANGFUSE_ENABLED:-false}"
LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"
LANGFUSE_HOST="${LANGFUSE_HOST:-}"
LANGFUSE_ENV="${LANGFUSE_ENV:-}"
LANGFUSE_PROMPT_LABEL="${LANGFUSE_PROMPT_LABEL:-production}"
COMMIT_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"

echo "Resolving ACR login server..."
ACR_LOGIN_SERVER="$(
  az acr show \
    --name "$AZURE_CONTAINER_REGISTRY_NAME" \
    --query loginServer \
    --output tsv
)"

IMAGE_TAG="${ACR_LOGIN_SERVER}/${BACKEND_IMAGE_NAME}:${IMAGE_TAG_SUFFIX}"
PREVIOUS_IMAGE="$(get_containerapp_image "$AZURE_BACKEND_CONTAINER_APP_NAME")"

echo "Building backend image in ACR as ${IMAGE_TAG}..."
if az acr build \
  --registry "$AZURE_CONTAINER_REGISTRY_NAME" \
  --image "${BACKEND_IMAGE_NAME}:${IMAGE_TAG_SUFFIX}" \
  --file apps/backend/Dockerfile \
  .; then
  echo "Remote build completed via ACR Tasks."
else
  echo "ACR Tasks not available in this subscription. Falling back to local Docker build + push..."
  require_cmd docker
  az acr login --name "$AZURE_CONTAINER_REGISTRY_NAME" >/dev/null
  docker build \
    -f apps/backend/Dockerfile \
    -t "$IMAGE_TAG" \
    .
  docker push "$IMAGE_TAG"
fi

echo "Updating backend Container App..."
SECRET_ARGS=()
if [ -n "$AZURE_DOCUMENT_INTELLIGENCE_API_KEY" ]; then
  SECRET_ARGS+=("docintel-key=${AZURE_DOCUMENT_INTELLIGENCE_API_KEY}")
fi
if [ -n "$AZURE_OPENAI_API_KEY" ]; then
  SECRET_ARGS+=("openai-key=${AZURE_OPENAI_API_KEY}")
fi
if [ -n "$LANGFUSE_PUBLIC_KEY" ]; then
  SECRET_ARGS+=("langfuse-public-key=${LANGFUSE_PUBLIC_KEY}")
fi
if [ -n "$LANGFUSE_SECRET_KEY" ]; then
  SECRET_ARGS+=("langfuse-secret-key=${LANGFUSE_SECRET_KEY}")
fi

if [ "${#SECRET_ARGS[@]}" -gt 0 ]; then
  az containerapp secret set \
    --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --secrets "${SECRET_ARGS[@]}" \
    --output none
fi

UPDATE_ARGS=(
  --name "$AZURE_BACKEND_CONTAINER_APP_NAME"
  --resource-group "$AZURE_RESOURCE_GROUP"
  --image "$IMAGE_TAG"
  --output none
)

ENV_ARGS=()
if [ -n "$AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT" ]; then
  ENV_ARGS+=("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=${AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT}")
fi
if [ -n "$AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID" ]; then
  ENV_ARGS+=("AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID=${AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID}")
fi
if [ -n "$AZURE_DOCUMENT_INTELLIGENCE_API_KEY" ]; then
  ENV_ARGS+=("AZURE_DOCUMENT_INTELLIGENCE_API_KEY=secretref:docintel-key")
fi
if [ -n "$AZURE_OPENAI_ENDPOINT" ]; then
  ENV_ARGS+=("AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}")
fi
if [ -n "$AZURE_OPENAI_PDF_PARSER_DEPLOYMENT" ]; then
  ENV_ARGS+=("AZURE_OPENAI_PDF_PARSER_DEPLOYMENT=${AZURE_OPENAI_PDF_PARSER_DEPLOYMENT}")
fi
if [ -n "$AZURE_OPENAI_TRANSACTION_CATEGORY_DEPLOYMENT" ]; then
  ENV_ARGS+=(
    "AZURE_OPENAI_TRANSACTION_CATEGORY_DEPLOYMENT=${AZURE_OPENAI_TRANSACTION_CATEGORY_DEPLOYMENT}"
  )
fi
if [ -n "$AZURE_OPENAI_API_VERSION" ]; then
  ENV_ARGS+=("AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}")
fi
if [ -n "$AZURE_OPENAI_API_KEY" ]; then
  ENV_ARGS+=("AZURE_OPENAI_API_KEY=secretref:openai-key")
fi
ENV_ARGS+=("LANGFUSE_ENABLED=${LANGFUSE_ENABLED}")
if [ -n "$LANGFUSE_PUBLIC_KEY" ]; then
  ENV_ARGS+=("LANGFUSE_PUBLIC_KEY=secretref:langfuse-public-key")
fi
if [ -n "$LANGFUSE_SECRET_KEY" ]; then
  ENV_ARGS+=("LANGFUSE_SECRET_KEY=secretref:langfuse-secret-key")
fi
if [ -n "$LANGFUSE_HOST" ]; then
  ENV_ARGS+=("LANGFUSE_HOST=${LANGFUSE_HOST}")
fi
if [ -n "$LANGFUSE_ENV" ]; then
  ENV_ARGS+=("LANGFUSE_ENV=${LANGFUSE_ENV}")
fi
if [ -n "$LANGFUSE_PROMPT_LABEL" ]; then
  ENV_ARGS+=("LANGFUSE_PROMPT_LABEL=${LANGFUSE_PROMPT_LABEL}")
fi

if [ "${#ENV_ARGS[@]}" -gt 0 ]; then
  UPDATE_ARGS+=(--set-env-vars "${ENV_ARGS[@]}")
fi

az containerapp update "${UPDATE_ARGS[@]}"

BACKEND_FQDN="$(
  az containerapp show \
    --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv
)"
BACKEND_URL="https://${BACKEND_FQDN}"

echo
echo "Backend deploy completed."
echo "Image:  ${IMAGE_TAG}"
echo "URL:    ${BACKEND_URL}"

notify_deploy "backend" "prod" "$IMAGE_TAG" "$BACKEND_URL" "$COMMIT_SHA" "$PREVIOUS_IMAGE"
