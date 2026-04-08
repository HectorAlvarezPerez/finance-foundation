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

AZURE_GITHUB_APP_NAME="${AZURE_GITHUB_APP_NAME:-finance-foundation-gha}"
GITHUB_ENVIRONMENT="${GITHUB_ENVIRONMENT:-production}"

require_var AZURE_RESOURCE_GROUP
require_var GITHUB_REPOSITORY

RESOURCE_GROUP_ID="$(
  az group show \
    --name "$AZURE_RESOURCE_GROUP" \
    --query id \
    --output tsv
)"
SUBSCRIPTION_ID="$(
  az account show \
    --query id \
    --output tsv
)"
TENANT_ID="$(
  az account show \
    --query tenantId \
    --output tsv
)"

echo "Creating Microsoft Entra application..."
APP_ID="$(
  az ad app create \
    --display-name "$AZURE_GITHUB_APP_NAME" \
    --query appId \
    --output tsv
)"

echo "Creating service principal..."
az ad sp create --id "$APP_ID" --output none

echo "Granting Contributor on resource group..."
az role assignment create \
  --assignee "$APP_ID" \
  --role Contributor \
  --scope "$RESOURCE_GROUP_ID" \
  --output none || true

echo "Configuring federated credential for GitHub Actions..."
cat <<EOF >/tmp/finance-foundation-fed-cred.json
{
  "name": "github-${GITHUB_ENVIRONMENT}",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:${GITHUB_REPOSITORY}:environment:${GITHUB_ENVIRONMENT}",
  "description": "OIDC trust for ${GITHUB_REPOSITORY} (${GITHUB_ENVIRONMENT})",
  "audiences": [
    "api://AzureADTokenExchange"
  ]
}
EOF

az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters @/tmp/finance-foundation-fed-cred.json \
  --output none

echo
echo "GitHub OIDC setup completed."
echo "Add these GitHub Action secrets in the 'production' environment:"
echo "  AZURE_CLIENT_ID=$APP_ID"
echo "  AZURE_TENANT_ID=$TENANT_ID"
echo "  AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID"
echo
echo "Add or confirm these GitHub Action variables:"
echo "  AZURE_RESOURCE_GROUP=$AZURE_RESOURCE_GROUP"
echo "  AZURE_CONTAINER_REGISTRY_NAME=<your-acr-name>"
echo "  AZURE_BACKEND_CONTAINER_APP_NAME=<your-backend-container-app>"
echo "  AZURE_FRONTEND_CONTAINER_APP_NAME=<your-frontend-container-app>"
echo "  NEXT_PUBLIC_API_BASE_URL_PROD=https://<your-backend-fqdn>/api/v1"
echo "  AZURE_OPENAI_ENDPOINT=<your-azure-openai-endpoint>            # optional for deploy summaries"
echo "  AZURE_OPENAI_API_VERSION=2025-03-01-preview                   # optional for deploy summaries"
echo "  AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT=<your-summary-model>   # optional for deploy summaries"
echo "  LANGFUSE_DEPLOY_SUMMARY_PROMPT_NAME=deploy_summary_notification # optional for deploy summaries"
echo
echo "Optional GitHub Action secrets for deploy notifications:"
echo "  SLACK_WEBHOOK_URL=<incoming-webhook-url>"
echo "  AZURE_OPENAI_API_KEY=<reuse-existing-key>"
