# frontend

Next.js frontend for `finance-foundation`.

## Responsibilities

- dashboard
- transactions
- accounts
- categories
- budgets
- insights
- settings
- auth screens (`/login`, `/register`)
- authenticated shell and navigation
- consumption of shared contracts from `@finance-foundation/shared`

## Local development

From the repo root:

```bash
npm run dev:frontend
```

From this workspace:

```bash
npm run dev
```

## Notes

- The app uses App Router.
- The authenticated area lives under `src/app/app`.
- API requests are centralized in `src/lib/api.ts`.
- The project no longer uses the default Next.js scaffold assets.
