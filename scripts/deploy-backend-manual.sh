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
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="${AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT:-}"
AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID="${AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID:-prebuilt-layout}"
AZURE_DOCUMENT_INTELLIGENCE_API_KEY="${AZURE_DOCUMENT_INTELLIGENCE_API_KEY:-}"
AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-}"
AZURE_OPENAI_PDF_PARSER_DEPLOYMENT="${AZURE_OPENAI_PDF_PARSER_DEPLOYMENT:-}"
AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION:-2025-03-01-preview}"
AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY:-}"

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
SECRET_ARGS=()
if [ -n "$AZURE_DOCUMENT_INTELLIGENCE_API_KEY" ]; then
  SECRET_ARGS+=("docintel-key=${AZURE_DOCUMENT_INTELLIGENCE_API_KEY}")
fi
if [ -n "$AZURE_OPENAI_API_KEY" ]; then
  SECRET_ARGS+=("openai-key=${AZURE_OPENAI_API_KEY}")
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
if [ -n "$AZURE_OPENAI_API_VERSION" ]; then
  ENV_ARGS+=("AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}")
fi
if [ -n "$AZURE_OPENAI_API_KEY" ]; then
  ENV_ARGS+=("AZURE_OPENAI_API_KEY=secretref:openai-key")
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

echo
echo "Backend deploy completed."
echo "Image:  ${IMAGE_TAG}"
echo "URL:    https://${BACKEND_FQDN}"
