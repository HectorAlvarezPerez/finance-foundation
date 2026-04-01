#!/usr/bin/env bash
set -euo pipefail

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required variable: $name" >&2
    exit 1
  fi
}

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) is required. Install it or run this script from Azure Cloud Shell." >&2
  exit 1
fi

AZURE_LOCATION="${AZURE_LOCATION:-westeurope}"
AZURE_POSTGRES_DATABASE_NAME="${AZURE_POSTGRES_DATABASE_NAME:-financefoundation}"
AZURE_BACKEND_CONTAINER_APP_NAME="${AZURE_BACKEND_CONTAINER_APP_NAME:-finance-foundation-backend}"
AZURE_FRONTEND_CONTAINER_APP_NAME="${AZURE_FRONTEND_CONTAINER_APP_NAME:-finance-foundation-frontend}"
GOOGLE_OAUTH_REDIRECT_PATH="${GOOGLE_OAUTH_REDIRECT_PATH:-/api/v1/auth/google/callback}"
PLACEHOLDER_IMAGE="${PLACEHOLDER_IMAGE:-mcr.microsoft.com/azuredocs/containerapps-helloworld:latest}"
POSTGRES_SKU="${POSTGRES_SKU:-Standard_B1ms}"
POSTGRES_TIER="${POSTGRES_TIER:-Burstable}"
POSTGRES_STORAGE_GB="${POSTGRES_STORAGE_GB:-32}"

require_var AZURE_RESOURCE_GROUP
require_var AZURE_CONTAINER_REGISTRY_NAME
require_var AZURE_CONTAINERAPPS_ENV_NAME
require_var AZURE_KEY_VAULT_NAME
require_var AZURE_POSTGRES_SERVER_NAME
require_var AZURE_POSTGRES_ADMIN_USERNAME
require_var AZURE_POSTGRES_ADMIN_PASSWORD
require_var SESSION_SECRET_KEY

echo "Installing Azure Container Apps extension if needed..."
az extension add --name containerapp --upgrade >/dev/null

echo "Creating resource group..."
az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --output none

echo "Creating Azure Container Registry..."
az acr create \
  --name "$AZURE_CONTAINER_REGISTRY_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --sku Basic \
  --admin-enabled false \
  --output none

echo "Creating Key Vault..."
az keyvault create \
  --name "$AZURE_KEY_VAULT_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --output none

CALLER_IP="${AZURE_DB_ALLOWED_IP:-$(curl -fsSL https://api.ipify.org)}"

echo "Creating PostgreSQL Flexible Server..."
az postgres flexible-server create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$AZURE_POSTGRES_SERVER_NAME" \
  --location "$AZURE_LOCATION" \
  --admin-user "$AZURE_POSTGRES_ADMIN_USERNAME" \
  --admin-password "$AZURE_POSTGRES_ADMIN_PASSWORD" \
  --sku-name "$POSTGRES_SKU" \
  --tier "$POSTGRES_TIER" \
  --storage-size "$POSTGRES_STORAGE_GB" \
  --public-access "$CALLER_IP" \
  --yes \
  --output none

echo "Creating PostgreSQL database..."
az postgres flexible-server db create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --server-name "$AZURE_POSTGRES_SERVER_NAME" \
  --database-name "$AZURE_POSTGRES_DATABASE_NAME" \
  --output none

echo "Creating Container Apps environment..."
az containerapp env create \
  --name "$AZURE_CONTAINERAPPS_ENV_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --output none

echo "Creating backend Container App..."
az containerapp create \
  --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --environment "$AZURE_CONTAINERAPPS_ENV_NAME" \
  --image "$PLACEHOLDER_IMAGE" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 2 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --system-assigned \
  --output none

echo "Creating frontend Container App..."
az containerapp create \
  --name "$AZURE_FRONTEND_CONTAINER_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --environment "$AZURE_CONTAINERAPPS_ENV_NAME" \
  --image "$PLACEHOLDER_IMAGE" \
  --target-port 3000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 2 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --system-assigned \
  --output none

BACKEND_FQDN="$(
  az containerapp show \
    --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv
)"
FRONTEND_FQDN="$(
  az containerapp show \
    --name "$AZURE_FRONTEND_CONTAINER_APP_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv
)"
BACKEND_PRINCIPAL_ID="$(
  az containerapp show \
    --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query identity.principalId \
    --output tsv
)"
FRONTEND_PRINCIPAL_ID="$(
  az containerapp show \
    --name "$AZURE_FRONTEND_CONTAINER_APP_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query identity.principalId \
    --output tsv
)"
ACR_ID="$(
  az acr show \
    --name "$AZURE_CONTAINER_REGISTRY_NAME" \
    --query id \
    --output tsv
)"
ACR_LOGIN_SERVER="$(
  az acr show \
    --name "$AZURE_CONTAINER_REGISTRY_NAME" \
    --query loginServer \
    --output tsv
)"

echo "Granting AcrPull to Container Apps managed identities..."
az role assignment create \
  --assignee-object-id "$BACKEND_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull \
  --scope "$ACR_ID" \
  --output none || true

az role assignment create \
  --assignee-object-id "$FRONTEND_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull \
  --scope "$ACR_ID" \
  --output none || true

echo "Configuring registry access on Container Apps..."
az containerapp registry set \
  --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --server "$ACR_LOGIN_SERVER" \
  --identity system \
  --output none

az containerapp registry set \
  --name "$AZURE_FRONTEND_CONTAINER_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --server "$ACR_LOGIN_SERVER" \
  --identity system \
  --output none

DATABASE_URL="postgresql+psycopg://${AZURE_POSTGRES_ADMIN_USERNAME}:${AZURE_POSTGRES_ADMIN_PASSWORD}@${AZURE_POSTGRES_SERVER_NAME}.postgres.database.azure.com:5432/${AZURE_POSTGRES_DATABASE_NAME}?sslmode=require"
GOOGLE_REDIRECT_URI="https://${BACKEND_FQDN}${GOOGLE_OAUTH_REDIRECT_PATH}"

echo "Saving core secrets in Key Vault..."
az keyvault secret set --vault-name "$AZURE_KEY_VAULT_NAME" --name database-url --value "$DATABASE_URL" --output none
az keyvault secret set --vault-name "$AZURE_KEY_VAULT_NAME" --name session-secret-key --value "$SESSION_SECRET_KEY" --output none

if [[ -n "${GOOGLE_OAUTH_CLIENT_ID:-}" ]]; then
  az keyvault secret set --vault-name "$AZURE_KEY_VAULT_NAME" --name google-oauth-client-id --value "$GOOGLE_OAUTH_CLIENT_ID" --output none
fi

if [[ -n "${GOOGLE_OAUTH_CLIENT_SECRET:-}" ]]; then
  az keyvault secret set --vault-name "$AZURE_KEY_VAULT_NAME" --name google-oauth-client-secret --value "$GOOGLE_OAUTH_CLIENT_SECRET" --output none
fi

echo "Applying backend runtime configuration..."
BACKEND_SECRETS=(
  "database-url=$DATABASE_URL"
  "session-secret-key=$SESSION_SECRET_KEY"
)

if [[ -n "${GOOGLE_OAUTH_CLIENT_ID:-}" ]]; then
  BACKEND_SECRETS+=("google-oauth-client-id=$GOOGLE_OAUTH_CLIENT_ID")
fi

if [[ -n "${GOOGLE_OAUTH_CLIENT_SECRET:-}" ]]; then
  BACKEND_SECRETS+=("google-oauth-client-secret=$GOOGLE_OAUTH_CLIENT_SECRET")
fi

az containerapp secret set \
  --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --secrets "${BACKEND_SECRETS[@]}" \
  --output none

BACKEND_ENV_VARS=(
  "APP_ENV=production"
  "DATABASE_URL=secretref:database-url"
  "FRONTEND_ORIGIN=https://${FRONTEND_FQDN}"
  "SESSION_SECRET_KEY=secretref:session-secret-key"
  "SESSION_COOKIE_SECURE=true"
  "SESSION_COOKIE_SAMESITE=lax"
  "ALLOW_DEV_USER_HEADER=false"
  "GOOGLE_OAUTH_REDIRECT_URI=${GOOGLE_REDIRECT_URI}"
)

if [[ -n "${GOOGLE_OAUTH_CLIENT_ID:-}" ]]; then
  BACKEND_ENV_VARS+=("GOOGLE_OAUTH_CLIENT_ID=secretref:google-oauth-client-id")
fi

if [[ -n "${GOOGLE_OAUTH_CLIENT_SECRET:-}" ]]; then
  BACKEND_ENV_VARS+=("GOOGLE_OAUTH_CLIENT_SECRET=secretref:google-oauth-client-secret")
fi

az containerapp update \
  --name "$AZURE_BACKEND_CONTAINER_APP_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --set-env-vars "${BACKEND_ENV_VARS[@]}" \
  --output none

echo
echo "Bootstrap completed."
echo "Resource Group:        $AZURE_RESOURCE_GROUP"
echo "ACR:                   $AZURE_CONTAINER_REGISTRY_NAME"
echo "Key Vault:             $AZURE_KEY_VAULT_NAME"
echo "PostgreSQL server:     $AZURE_POSTGRES_SERVER_NAME"
echo "Container Apps env:    $AZURE_CONTAINERAPPS_ENV_NAME"
echo "Backend URL:           https://${BACKEND_FQDN}"
echo "Frontend URL:          https://${FRONTEND_FQDN}"
echo "Google redirect URI:   ${GOOGLE_REDIRECT_URI}"
echo
echo "Next steps:"
echo "1. Add GitHub vars: AZURE_RESOURCE_GROUP, AZURE_CONTAINER_REGISTRY_NAME, AZURE_BACKEND_CONTAINER_APP_NAME, AZURE_FRONTEND_CONTAINER_APP_NAME, NEXT_PUBLIC_API_BASE_URL_PROD=https://${BACKEND_FQDN}/api/v1"
echo "2. Configure GitHub OIDC with scripts/azure-setup-github-oidc.sh"
echo "3. Trigger backend and frontend deploy workflows from GitHub Actions"
