#!/usr/bin/env bash
set -euo pipefail

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

require_cmd az
require_cmd docker

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-finance-foundation-rg}"
AZURE_CONTAINER_REGISTRY_NAME="${AZURE_CONTAINER_REGISTRY_NAME:-financefoundationacr}"
AZURE_BACKEND_CONTAINER_APP_NAME="${AZURE_BACKEND_CONTAINER_APP_NAME:-finance-foundation-backend}"
BACKEND_IMAGE_NAME="${BACKEND_IMAGE_NAME:-finance-foundation-backend}"
IMAGE_TAG_SUFFIX="${IMAGE_TAG_SUFFIX:-manual-$(date +%Y%m%d%H%M%S)}"

echo "Resolving ACR login server..."
ACR_LOGIN_SERVER="$(
  az acr show \
    --name "$AZURE_CONTAINER_REGISTRY_NAME" \
    --query loginServer \
    --output tsv
)"

IMAGE_TAG="${ACR_LOGIN_SERVER}/${BACKEND_IMAGE_NAME}:${IMAGE_TAG_SUFFIX}"

echo "Building backend image in ACR as ${IMAGE_TAG}..."
if az acr build \
  --registry "$AZURE_CONTAINER_REGISTRY_NAME" \
  --image "${BACKEND_IMAGE_NAME}:${IMAGE_TAG_SUFFIX}" \
  --file apps/backend/Dockerfile \
  .; then
  echo "Remote build completed via ACR Tasks."
else
  echo "ACR Tasks not available in this subscription. Falling back to local Docker build + push..."
  az acr login --name "$AZURE_CONTAINER_REGISTRY_NAME" >/dev/null
  docker build \
    -f apps/backend/Dockerfile \
    -t "$IMAGE_TAG" \
    .
  docker push "$IMAGE_TAG"
fi

echo "Updating backend Container App..."
az containerapp update \
  --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --image "$IMAGE_TAG" \
  --output none

BACKEND_FQDN="$(
  az containerapp show \
    --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv
)"

echo
echo "Backend deploy completed."
echo "Image:  ${IMAGE_TAG}"
echo "URL:    https://${BACKEND_FQDN}"
