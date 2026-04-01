# Azure deployment baseline

Esta carpeta deja preparada la Fase 7 para desplegar `finance-foundation` en Azure con una estrategia simple:

- `apps/backend` en Azure Container Apps
- `apps/frontend` en Azure Container Apps
- imágenes almacenadas en Azure Container Registry (ACR)
- autenticación de GitHub Actions con OIDC

## Qué asume el repo

Los workflows de despliegue no crean toda la infraestructura desde cero. Asumen que ya existen:

- un Resource Group
- un Azure Container Registry
- una Azure Container Apps Environment
- una Container App para backend
- una Container App para frontend

Los workflows se encargan de:

- construir la imagen en ACR
- actualizar la Container App correspondiente

## Scripts incluidos

- [bootstrap.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/bootstrap.env.example)
- [github-oidc.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/github-oidc.env.example)
- [azure-bootstrap.sh](/home/hector/Escritorio/GitHub/finance-foundation/scripts/azure-bootstrap.sh)
- [azure-setup-github-oidc.sh](/home/hector/Escritorio/GitHub/finance-foundation/scripts/azure-setup-github-oidc.sh)

Flujo sugerido:

1. Copia `bootstrap.env.example` a un `.env` local y rellénalo.
2. Ejecuta `source <tu-archivo-env> && bash scripts/azure-bootstrap.sh`
3. Copia `github-oidc.env.example`, rellénalo y ejecuta `source <tu-archivo-env> && bash scripts/azure-setup-github-oidc.sh`
4. Añade en GitHub los secrets/vars que te imprimen los scripts.
5. Lanza manualmente los workflows de deploy.

## Variables y secretos en GitHub

### Secrets

Configura estos secrets en GitHub Actions, idealmente en el environment `production`:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

### Repository variables

- `AZURE_RESOURCE_GROUP`
- `AZURE_CONTAINER_REGISTRY_NAME`
- `AZURE_BACKEND_CONTAINER_APP_NAME`
- `AZURE_FRONTEND_CONTAINER_APP_NAME`
- `NEXT_PUBLIC_API_BASE_URL_PROD`

## Entorno del backend

Usa [backend.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/backend.env.example) como plantilla para los env vars/secrets de la Container App del backend.

Notas:

- usa `ALLOW_DEV_USER_HEADER=false` en producción
- si frontend y backend viven bajo el mismo dominio raíz, `SESSION_COOKIE_SAMESITE=lax` suele ser suficiente
- si acabas sirviendo frontend y backend desde sites distintos, cambia a `SESSION_COOKIE_SAMESITE=none`

## Entorno del frontend

Usa [frontend.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/frontend.env.example) como referencia. La variable `NEXT_PUBLIC_API_BASE_URL` se inyecta en build time desde el workflow.

## Bootstrap manual sugerido

Ejemplo orientativo con Azure CLI:

```bash
az group create --name finance-foundation-rg --location westeurope

az acr create \
  --name financefoundationacr \
  --resource-group finance-foundation-rg \
  --sku Basic

az containerapp env create \
  --name finance-foundation-env \
  --resource-group finance-foundation-rg \
  --location westeurope
```

Si prefieres no ejecutar los comandos uno a uno, usa directamente el script:

```bash
source infra/azure/bootstrap.env
bash scripts/azure-bootstrap.sh
```

Crea después las dos Container Apps iniciales, habilita ingress externo y asígnales identidad administrada. Luego concede `AcrPull` a ambas identidades sobre el ACR y configura el registry:

```bash
az containerapp registry set \
  --name <container-app-name> \
  --resource-group finance-foundation-rg \
  --server <acr-name>.azurecr.io \
  --identity system
```

## Workflows

- [backend-deploy.yml](/home/hector/Escritorio/GitHub/finance-foundation/.github/workflows/backend-deploy.yml)
- [frontend-deploy.yml](/home/hector/Escritorio/GitHub/finance-foundation/.github/workflows/frontend-deploy.yml)

Ambos se disparan manualmente con `workflow_dispatch` y usan OIDC con `azure/login@v2`.

## Requisito local

Para ejecutar los scripts necesitas Azure CLI (`az`) y la extensión de Container Apps. Si no lo tienes instalado en tu máquina, puedes ejecutarlos desde Azure Cloud Shell.
