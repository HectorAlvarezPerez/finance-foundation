# Azure deployment baseline

Esta carpeta deja preparada la Fase 7 para desplegar `finance-foundation` en Azure con una estrategia simple:

- `apps/backend` en Azure Container Apps
- `apps/frontend` en Azure Container Apps
- imágenes almacenadas en Azure Container Registry (ACR)
- autenticación de GitHub Actions con OIDC
- despliegues manuales y workflows de GitHub Actions que comparten la misma lógica de deploy

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
- reutilizar los scripts manuales de deploy para backend y frontend

## Notificaciones operativas de deploy

La integración con Slack es opcional y está pensada para notificaciones operativas de producción, no para chat de usuario final.

El flujo es no bloqueante:

- si `SLACK_WEBHOOK_URL` no está configurada, el deploy termina igual y simplemente no se envía mensaje
- si Slack falla, el deploy no se rompe
- si `gh` no está autenticado o no puede resolver contexto de PR, se degrada a contexto de commits o merge commit
- si Azure OpenAI no está disponible o no puede generar el párrafo narrativo, se usa un fallback determinista
- si Langfuse no está disponible o no puede resolver el prompt/trazas, se usa prompt local y se continúa sin romper el deploy

El mensaje de Slack debe incluir:

- servicio desplegado: `backend` o `frontend`
- entorno: `prod`
- commit SHA corto
- imagen o tag desplegado
- URL resultante
- un párrafo breve narrativo con el resumen del cambio

### Configuración

Reutiliza estas variables ya existentes:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`

Y añade esta variable específica para la notificación operativa:

- `SLACK_WEBHOOK_URL`
- `AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT`
- `LANGFUSE_DEPLOY_SUMMARY_PROMPT_NAME` (opcional, default `deploy_summary_notification`)

En workflows, el helper puede usar `GH_TOKEN` para intentar resolver la PR mergeada asociada al commit desplegado. Si no hay PR resoluble, el fallback usa el rango de commits o el merge/commit desplegado como contexto.

### Ejemplo de entorno

Usa [deploy-notifications.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/deploy-notifications.env.example) como plantilla para variables orientadas a despliegue y observabilidad operativa.

## Scripts incluidos

- [bootstrap.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/bootstrap.env.example)
- [github-oidc.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/github-oidc.env.example)
- [deploy-notifications.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/deploy-notifications.env.example)
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
- `AZURE_DOCUMENT_INTELLIGENCE_API_KEY`
- `AZURE_OPENAI_API_KEY`
- `SLACK_WEBHOOK_URL` si quieres activar la notificación operativa desde workflows

### Repository variables

- `AZURE_RESOURCE_GROUP`
- `AZURE_CONTAINER_REGISTRY_NAME`
- `AZURE_BACKEND_CONTAINER_APP_NAME`
- `AZURE_FRONTEND_CONTAINER_APP_NAME`
- `NEXT_PUBLIC_API_BASE_URL_PROD`
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`
- `AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_PDF_PARSER_DEPLOYMENT`
- `AZURE_OPENAI_TRANSACTION_CATEGORY_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOY_SUMMARY_DEPLOYMENT`
- `CLASSIFICATION_DEBUG`

## Entorno del backend

Usa [backend.env.example](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/backend.env.example) como plantilla para los env vars/secrets de la Container App del backend.

Notas:

- usa `ALLOW_DEV_USER_HEADER=false` en producción
- si frontend y backend viven bajo el mismo dominio raíz, `SESSION_COOKIE_SAMESITE=lax` suele ser suficiente
- si acabas sirviendo frontend y backend desde sites distintos, cambia a `SESSION_COOKIE_SAMESITE=none`
- si activas importación PDF con OCR/LLM o la clasificación asistida de categorías, configura también los env vars de Azure Document Intelligence y Azure OpenAI
- activa `CLASSIFICATION_DEBUG=true` sólo en desarrollo si quieres ver en backend y preview el motivo de clasificación por fila

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

Ambos se disparan manualmente con `workflow_dispatch`, usan OIDC con `azure/login@v2` y reutilizan los scripts manuales de deploy para mantener una sola lógica de despliegue.

El workflow de backend también:

- sincroniza los secrets del backend en la Container App
- actualiza los env vars de OCR, fallback LLM y clasificación asistida si están definidos en GitHub
- puede aprovechar `GH_TOKEN` para enriquecer la notificación operativa si la integración Slack está activada

## Deploy manual con Azure CLI

Si el tenant no permite crear App Registrations o federated credentials en Microsoft Entra ID, puedes desplegar igualmente sin GitHub OIDC haciendo el build y update desde tu sesión local de Azure CLI.

### Backend

```bash
ACR_NAME=financefoundationacr
RESOURCE_GROUP=finance-foundation-rg
BACKEND_APP=finance-foundation-backend
BACKEND_IMAGE_NAME=finance-foundation-backend

ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)"
IMAGE_TAG="$ACR_LOGIN_SERVER/$BACKEND_IMAGE_NAME:manual-$(date +%Y%m%d%H%M%S)"

az acr build \
  --registry "$ACR_NAME" \
  --image "${BACKEND_IMAGE_NAME}:${IMAGE_TAG##*:}" \
  --file apps/backend/Dockerfile \
  .

az containerapp update \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$IMAGE_TAG"
```

### Frontend

```bash
ACR_NAME=financefoundationacr
RESOURCE_GROUP=finance-foundation-rg
FRONTEND_APP=finance-foundation-frontend
FRONTEND_IMAGE_NAME=finance-foundation-frontend
NEXT_PUBLIC_API_BASE_URL="https://finance-foundation-backend.kindplant-dd9a519a.spaincentral.azurecontainerapps.io/api/v1"

ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)"
IMAGE_TAG="$ACR_LOGIN_SERVER/$FRONTEND_IMAGE_NAME:manual-$(date +%Y%m%d%H%M%S)"

az acr build \
  --registry "$ACR_NAME" \
  --image "${FRONTEND_IMAGE_NAME}:${IMAGE_TAG##*:}" \
  --file apps/frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL="$NEXT_PUBLIC_API_BASE_URL" \
  .

az containerapp update \
  --name "$FRONTEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$IMAGE_TAG"
```

Si además configuras `SLACK_WEBHOOK_URL` y las variables de Azure OpenAI para el resumen, el script de notificación operativa enviará un mensaje al final del despliegue sin impedir que el deploy termine bien.

## Requisito local

Para ejecutar los scripts necesitas Azure CLI (`az`) y la extensión de Container Apps. Si no lo tienes instalado en tu máquina, puedes ejecutarlos desde Azure Cloud Shell.
