set shell := ["bash", "-lc"]

default:
  just --list

# Install JS dependencies at the repo root.
install:
  npm install

# Export OpenAPI from FastAPI and regenerate TypeScript contracts.
contracts:
  npm run generate:contracts

# Start the backend in development with auto-reload.
backend:
  npm run dev:backend

# Start the backend in development with a local SQLite database and auto-reload.
backend-local:
  npm run dev:backend:local

# Start the frontend in development. Next.js handles reload automatically.
frontend:
  npm run dev:frontend

# Run frontend and backend together for day-to-day development.
dev:
  npx concurrently -k -n backend,frontend -c blue,green "npm run dev:backend:local" "npm run dev:frontend"

# Regenerate contracts and start the full development stack with reload.
up: contracts
  npx concurrently -k -n backend,frontend -c blue,green "npm run dev:backend:local" "npm run dev:frontend"

# Reset the demo database, seed it and build the demo frontend.
demo-setup:
  npm run demo:setup

# Start the demo backend and demo frontend together.
demo:
  npm run demo:start

# Start only the demo backend.
demo-backend:
  npm run demo:backend

# Start only the demo frontend.
demo-frontend:
  npm run demo:frontend

# Run the backend checks.
backend-check:
  npm run lint:backend
  npm run typecheck:backend
  npm run test:backend

# Run the frontend checks.
frontend-check:
  npm run lint:frontend
  npm run typecheck:frontend

# Run the full quality gate.
check:
  npm run quality

# Run the Playwright suite.
e2e:
  npm run test:e2e

# Useful local bootstrap after schema changes.
refresh:
  npm run generate:contracts
  npm run typecheck:frontend
  npm run typecheck:backend

# Reset demo data, rebuild the demo frontend and start the full demo stack.
demo-up:
  npm run demo:start

# Bootstrap Azure production infrastructure from env vars.
azure-bootstrap:
  bash scripts/azure-bootstrap.sh

# Configure GitHub Actions OIDC against Azure from env vars.
azure-oidc:
  bash scripts/azure-setup-github-oidc.sh
