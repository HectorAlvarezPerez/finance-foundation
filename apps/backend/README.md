# backend

FastAPI application for `finance-foundation`.

## Responsibilities

- auth
- transactions
- accounts
- categories
- budgets
- insights
- settings

## Local setup

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

For day-to-day work from the repo root, prefer [README.md](/home/hector/Escritorio/GitHub/finance-foundation/README.md) and:

```bash
npm run up
```

## Auth modes

The backend currently supports a pragmatic v1 plus an optional future path:

- `AUTH_MODE=local`
  - email/password stored in `user_credentials`
  - local session cookie owned by the backend
- optional direct Google OAuth
  - Google authenticates the user
  - the backend links or creates the user in `users`
  - the backend still owns the app session cookie
- future `AUTH_MODE=entra_external_id`
  - Microsoft Entra External ID as identity provider
  - the backend still owns the app session cookie
  - Google can be enabled inside the Entra user flow and exposed through the same backend callback

The source of truth for auth configuration is [config.py](/home/hector/Escritorio/GitHub/finance-foundation/apps/backend/app/core/config.py).

## Google OAuth (v1)

### Required env vars

Copy [apps/backend/.env.example](/home/hector/Escritorio/GitHub/finance-foundation/apps/backend/.env.example) to `.env` and fill at least:

```bash
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

`GOOGLE_OAUTH_METADATA_URL` already defaults to the Google OpenID Connect discovery document and normally does not need to change.

### Google Cloud checklist

1. Go to Google Cloud Console.
2. Configure the OAuth consent screen for your project.
3. Create an **OAuth client ID** of type **Web application**.
4. Add the backend callback as an authorized redirect URI:
   - local: `http://localhost:8000/api/v1/auth/google/callback`
   - production: `https://<your-backend-domain>/api/v1/auth/google/callback`
5. Copy the Google client ID into `GOOGLE_OAUTH_CLIENT_ID`.
6. Copy the Google client secret into `GOOGLE_OAUTH_CLIENT_SECRET`.

### How this repo uses Google OAuth

- The frontend shows the Google CTA only when `GET /api/v1/auth/providers` reports Google as enabled.
- Login starts at:
  - `/api/v1/auth/google/start`
- Google redirects back to:
  - `/api/v1/auth/google/callback`
- The backend validates the Google ID token, links or creates the user in `users`, and then sets the app session cookie.

This keeps the same session model as local auth while adding social login with very little surface area.

## Microsoft Entra External ID (future)

### Required env vars

Copy [apps/backend/.env.example](/home/hector/Escritorio/GitHub/finance-foundation/apps/backend/.env.example) to `.env` and fill at least:

```bash
AUTH_MODE=entra_external_id
ENTRA_CLIENT_ID=...
ENTRA_CLIENT_SECRET=...
ENTRA_METADATA_URL=...
ENTRA_REDIRECT_URI=http://localhost:8000/api/v1/auth/entra/callback
```

Recommended during local development:

```bash
FRONTEND_ORIGIN=http://localhost:3000,http://localhost:3100
SESSION_COOKIE_SECURE=false
```

In production, switch `SESSION_COOKIE_SECURE=true` and use your public frontend/backend origins.

### Portal checklist

1. Create or choose a **Microsoft Entra External ID** tenant for customer-facing auth.
2. Register a **web application** in that tenant.
3. Add a **client secret** for local/dev use.
4. Add the backend callback as a **web redirect URI**:
   - local: `http://localhost:8000/api/v1/auth/entra/callback`
   - production: `https://<your-backend-domain>/api/v1/auth/entra/callback`
5. Copy the app's **Application (client) ID** into `ENTRA_CLIENT_ID`.
6. Copy the generated secret into `ENTRA_CLIENT_SECRET`.
7. Copy the tenant/user flow **OpenID Connect discovery document** URL into `ENTRA_METADATA_URL`.
8. Create or select the **sign-up and sign-in user flow** that your app will use.
9. Enable the sign-up / sign-in experience you want for the app.
10. If you want Google login, add Google as an identity provider in the external tenant and enable it in the relevant user flow.

### Google setup checklist

1. Create a Google OAuth web app.
2. In the Google OAuth consent screen, add `ciamlogin.com` and `microsoftonline.com` as authorized domains if Google asks for them.
3. Add the redirect URIs required by Microsoft Entra External ID in the Google console.
4. Copy the Google client ID/secret into the Entra External ID Google provider configuration.
5. Enable Google inside the user flow that your app uses.

### How this repo uses External ID

- The frontend shows provider CTAs only when `GET /api/v1/auth/providers` reports them as enabled.
- Login starts at:
  - `/api/v1/auth/entra/start`
- Entra redirects back to:
  - `/api/v1/auth/entra/callback`
- The backend validates the ID token, links or creates the user in `users`, and then sets the app session cookie.

This means the app keeps a single session model even when authentication is delegated to Entra.

## References

- Google OpenID Connect: [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- Google web app setup: [Set up OAuth 2.0](https://support.google.com/cloud/answer/6158849)
- Microsoft states that **Azure AD B2C is no longer available to purchase for new customers as of May 1, 2025**, so this repo targets External ID for new setups: [What is Azure Active Directory B2C?](https://learn.microsoft.com/en-us/azure/active-directory-b2c/overview)
- Redirect URI guidance: [How to add a redirect URI to your application](https://learn.microsoft.com/en-us/entra/identity-platform/how-to-add-redirect-uri)
- External tenant identity providers overview: [Identity providers for external tenants](https://learn.microsoft.com/en-us/azure/active-directory/external-identities/customers/concept-authentication-methods-customers)
- User flow setup: [Create a sign-up and sign-in user flow](https://learn.microsoft.com/en-us/entra/external-id/customers/how-to-user-flow-sign-up-sign-in-customers)
- Google provider setup for external tenants: [Add Google as an identity provider - Microsoft Entra External ID](https://learn.microsoft.com/en-us/entra/external-id/customers/how-to-google-federation-customers)
