# Finance Foundation

Monorepo de la aplicación de finanzas personales, con frontend en Next.js y backend en FastAPI.

## Estructura

- `apps/frontend`: aplicación web con Next.js, App Router y Tailwind CSS.
- `apps/backend`: API con FastAPI, SQLAlchemy y Alembic.
- `packages/shared`: contratos TypeScript derivados del OpenAPI del backend para que frontend consuma la API con el backend como source of truth.
- `scripts`: automatizaciones locales para demo y E2E.

## Filosofía del repo

- `apps/` contiene aplicaciones ejecutables, con su runtime, build y despliegue propios.
- `packages/` debe contener solo código reutilizable y agnóstico del runtime.
- Los tests E2E del frontend viven en [apps/frontend/tests/e2e](/home/hector/Escritorio/GitHub/finance-foundation/apps/frontend/tests/e2e).
- La configuración de Playwright vive en [apps/frontend/playwright.config.ts](/home/hector/Escritorio/GitHub/finance-foundation/apps/frontend/playwright.config.ts).

## Requisitos

- Node.js y npm
- `uv` para el backend Python

## Primer arranque

Si es la primera vez que levantas el proyecto, este es el orden recomendado:

```bash
npm install
cd apps/backend && uv sync && cd ../..
cp apps/backend/.env.example apps/backend/.env
npm run demo:start
```

Qué hace cada paso:

1. `npm install`: instala las dependencias del monorepo y del frontend.
2. `cd apps/backend && uv sync && cd ../..`: crea o actualiza la `.venv` del backend con sus dependencias.
3. `cp apps/backend/.env.example apps/backend/.env`: deja preparado el entorno local del backend.
4. `npm run demo:start`: prepara la base demo, siembra datos y levanta backend y frontend en modo demo.

Después abre [http://localhost:3100](http://localhost:3100).

## Scripts principales

### Desarrollo

```bash
npm run up
```

- `up`: regenera contratos desde el OpenAPI del backend y levanta backend + frontend con reload automático.

Si quieres levantar cada parte por separado:

```bash
npm run dev:backend:local
npm run dev:frontend
```

- `dev:backend:local`: arranca FastAPI en modo desarrollo contra SQLite local (`apps/backend/dev-app.db`) y aplica migraciones antes de iniciar.
- `dev:frontend`: arranca Next.js en modo desarrollo.

### Contratos compartidos

```bash
npm run generate:contracts
```

- exporta el schema OpenAPI del backend a `packages/shared/openapi.json`
- genera los tipos TypeScript en `packages/shared/src/generated/api.ts`
- permite que el frontend lea contratos reales de la API sin duplicarlos a mano

### Demo local

```bash
npm run demo:start
```

Esto hace lo siguiente:

1. recrea la base demo local `apps/backend/dev-app.db`
2. aplica migraciones
3. siembra los datos demo
4. builda el frontend
5. levanta backend demo en `8100`
6. levanta frontend demo en `3100`

Después abre [http://localhost:3100](http://localhost:3100).

Credenciales demo:

- email: `demo@finance-foundation.app`
- password: `Demo12345`

## Scripts `.sh`

Los scripts de [scripts](/home/hector/Escritorio/GitHub/finance-foundation/scripts) no se ejecutan solos; corren cuando los invoca un comando npm o cuando los lanzas explícitamente.

### `scripts/demo-setup.sh`

Se usa en:

- `npm run demo:setup`
- `npm run demo:start`

Responsabilidad:

- borrar `apps/backend/dev-app.db`
- aplicar migraciones
- ejecutar la seed demo
- hacer build del frontend apuntando a la API demo

### `scripts/demo-backend.sh`

Se usa en:

- `npm run demo:backend`
- `npm run demo:start`

Responsabilidad:

- arrancar el backend demo usando `apps/backend/dev-app.db`

### `scripts/demo-frontend.sh`

Se usa en:

- `npm run demo:frontend`
- `npm run demo:start`

Responsabilidad:

- arrancar el frontend demo compilado en `3100`

### `scripts/e2e-backend.sh`

Se usa en:

- `npm run test:e2e`

Responsabilidad:

- crear una base aislada para E2E: `apps/backend/e2e-app.db`
- aplicar migraciones
- sembrar los datos demo
- arrancar el backend temporal para Playwright

Importante:

- este backend E2E está separado del backend demo
- los tests de Playwright no deberían contaminar `dev-app.db`

## Tests y calidad

### Frontend

```bash
npm run lint:frontend
npm run typecheck:frontend
```

### Backend

```bash
npm run lint:backend
npm run typecheck:backend
npm run test:backend
```

### End-to-end

```bash
npm run test:e2e
```

Esto ejecuta Playwright desde el workspace del frontend y ahora levanta:

- un backend aislado para E2E en `8000`
- el frontend en `3000`

sin depender de que ya tengas la app arrancada a mano.

### CI

GitHub Actions queda dividido en dos workflows:

- `.github/workflows/quality.yml`: checks rápidos y estables
- `.github/workflows/e2e.yml`: suite Playwright separada con artefactos

El workflow de quality ejecuta:

```bash
npm run quality
```

Eso incluye:

- regenerar contratos y comprobar que no hay drift
- lint y typecheck del frontend
- lint, typecheck y tests del backend

El workflow de E2E ejecuta:

```bash
npm run test:e2e
```

e instala Chromium antes de lanzar Playwright.

## Artefactos generados

- Los artefactos de Playwright se guardan dentro de `apps/frontend/.playwright/`.
- No deberían versionarse.
- La demo local usa `apps/backend/dev-app.db`.
- Los tests E2E usan `apps/backend/e2e-app.db`.

## Despliegue

La base de despliegue de Fase 7 vive en [infra/azure/README.md](/home/hector/Escritorio/GitHub/finance-foundation/infra/azure/README.md).

Incluye:

- Dockerfiles listos para producción para frontend y backend
- workflows manuales de GitHub Actions para desplegar a Azure Container Apps
- plantillas de entorno para backend y frontend

Workflows disponibles:

- [backend-deploy.yml](/home/hector/Escritorio/GitHub/finance-foundation/.github/workflows/backend-deploy.yml)
- [frontend-deploy.yml](/home/hector/Escritorio/GitHub/finance-foundation/.github/workflows/frontend-deploy.yml)

Estos workflows asumen que la infraestructura de Azure ya existe y actualizan las Container Apps con una imagen nueva construida en ACR.

## Estado actual

- frontend y backend conectados
- demo local funcional
- suite E2E básica con auth, navegación y CRUD principal
- estructura preparada para seguir moviendo contratos compartidos a `packages/shared`
