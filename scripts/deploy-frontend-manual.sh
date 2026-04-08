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
    if uv run --with "langfuse>=3.0.0" python3 scripts/deploy-notify.py "${args[@]}"; then
      return 0
    fi
  fi

  python3 scripts/deploy-notify.py "${args[@]}" || true
}

require_cmd az

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finance-foundation-rg}"
AZURE_CONTAINER_REGISTRY_NAME="${AZURE_CONTAINER_REGISTRY_NAME:-financefoundationacr}"
AZURE_BACKEND_CONTAINER_APP_NAME="${AZURE_BACKEND_CONTAINER_APP_NAME:-finance-foundation-backend}"
AZURE_FRONTEND_CONTAINER_APP_NAME="${AZURE_FRONTEND_CONTAINER_APP_NAME:-finance-foundation-frontend}"
FRONTEND_IMAGE_NAME="${FRONTEND_IMAGE_NAME:-finance-foundation-frontend}"
IMAGE_TAG_SUFFIX="${IMAGE_TAG_SUFFIX:-manual-$(date +%Y%m%d%H%M%S)}"
AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT="${AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT:-${AZURE_OPENAI_TRANSACTION_CATEGORY_DEPLOYMENT:-}}"
COMMIT_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"

echo "Resolving ACR login server..."
ACR_LOGIN_SERVER="$(
  az acr show \
    --name "$AZURE_CONTAINER_REGISTRY_NAME" \
    --query loginServer \
    --output tsv
)"

if [ -n "${NEXT_PUBLIC_API_BASE_URL:-}" ]; then
  NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL}"
else
  echo "Resolving backend FQDN for NEXT_PUBLIC_API_BASE_URL..."
  BACKEND_FQDN="$(
    az containerapp show \
      --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
      --resource-group "$AZURE_RESOURCE_GROUP" \
      --query properties.configuration.ingress.fqdn \
      --output tsv
  )"
  NEXT_PUBLIC_API_BASE_URL="https://${BACKEND_FQDN}/api/v1"
fi

IMAGE_TAG="${ACR_LOGIN_SERVER}/${FRONTEND_IMAGE_NAME}:${IMAGE_TAG_SUFFIX}"
PREVIOUS_IMAGE="$(get_containerapp_image "$AZURE_FRONTEND_CONTAINER_APP_NAME")"

echo "Building frontend image in ACR as ${IMAGE_TAG}..."
if az acr build \
  --registry "$AZURE_CONTAINER_REGISTRY_NAME" \
  --image "${FRONTEND_IMAGE_NAME}:${IMAGE_TAG_SUFFIX}" \
  --file apps/frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL="$NEXT_PUBLIC_API_BASE_URL" \
  .; then
  echo "Remote build completed via ACR Tasks."
else
  echo "ACR Tasks not available in this subscription. Falling back to local Docker build + push..."
  require_cmd docker
  az acr login --name "$AZURE_CONTAINER_REGISTRY_NAME" >/dev/null
  docker build \
    -f apps/frontend/Dockerfile \
    --build-arg NEXT_PUBLIC_API_BASE_URL="$NEXT_PUBLIC_API_BASE_URL" \
    -t "$IMAGE_TAG" \
    .
  docker push "$IMAGE_TAG"
fi

echo "Updating frontend Container App..."
az containerapp update \
  --name "$AZURE_FRONTEND_CONTAINER_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --image "$IMAGE_TAG" \
  --output none

FRONTEND_FQDN="$(
  az containerapp show \
    --name "$AZURE_FRONTEND_CONTAINER_APP_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv
)"
FRONTEND_URL="https://${FRONTEND_FQDN}"

echo
echo "Frontend deploy completed."
echo "Image:  ${IMAGE_TAG}"
echo "URL:    ${FRONTEND_URL}"
echo "API:    ${NEXT_PUBLIC_API_BASE_URL}"

notify_deploy "frontend" "prod" "$IMAGE_TAG" "$FRONTEND_URL" "$COMMIT_SHA" "$PREVIOUS_IMAGE"
