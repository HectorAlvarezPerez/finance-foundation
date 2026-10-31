# shared

Shared package for cross-app contracts and utilities.

This package now contains the TypeScript contracts consumed by the frontend.

Source of truth:

- Backend FastAPI schemas and routes
- OpenAPI exported from the backend

Workflow:

```bash
npm run generate:contracts
```

This command:

- exports `openapi.json` from the backend
- generates TypeScript definitions into `src/generated/api.ts`
- exposes friendly aliases through `src/contracts.ts`

Local task runner:

```bash
npm run just -- up
```

This uses `uvx --from rust-just just ...`, so `just` does not need to be installed globally.
