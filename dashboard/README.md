# Hospital VoiceAgent — dashboard

A read-only web UI over the backend's REST API: an overview of headline
counts, patients (with filters), patient detail (demographics, insurance,
edit history, calls), calls (transcript, summary, recording), and logs
(everything Retell sent and the backend did, filterable by time range,
level, event and call). All writes go through the voice agent or the REST
API.

## Running it

```bash
cd dashboard
npm install
cp .env.example .env.local   # set VITE_API_BASE_URL and VITE_API_KEY
npm run dev                  # http://localhost:5173
```

- `VITE_API_BASE_URL` sets which backend to talk to. Without it, the
  dashboard uses the Railway deployment.
- `VITE_API_KEY` is the backend's `API_KEY`. When it's set,
  there's no sign-in screen. Leave it unset on any publicly hosted build,
  because `VITE_*` values are compiled into the JavaScript. Without it, the
  dashboard asks for the key and keeps it only for the browser tab.

The backend must allow the dashboard's origin in `CORS_ORIGINS`
(`http://localhost:5173` is allowed by default).

| Script | |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` | Typecheck + standalone production build to `dist/` |
| `npm run build:backend` | Build the copy the backend serves at `/dashboard`, into `backend/assets/dashboard/`. Commit the result. |
| `npm test` | Vitest |
| `npm run gen:api` | Regenerate `src/types/api.d.ts` from the backend's `/openapi.json`. Needs the backend's key in `API_KEY` (PowerShell: `$env:API_KEY="..."`); `redocly.yaml` sends it. |

## Served by the backend

The live dashboard is at `<backend URL>/dashboard`. Railway only builds the
Python backend, so that copy is built here with `npm run build:backend` and
committed. Re-run it and commit after changing the dashboard. That build:

- loads under `/dashboard/` and calls the API on the same server, so no CORS
  setup is needed;
- has no sign-in screen. The backend asks for the API key (the browser's login
  prompt) before serving the page, then sets a session cookie that the
  dashboard's API calls carry. `VITE_API_KEY` and `VITE_API_BASE_URL` from
  `.env.local` are forced empty in this mode, so a local key can never end up
  in the committed bundle.

## Stack, and why

- **Vite + TypeScript**: an internal SPA hitting the FastAPI backend. There's
  no SEO/SSR need, so no Next.js.
- **TanStack Query** for all server state (fetching, caching, pagination,
  loading/error states). No hand-rolled fetch/useEffect data logic.
- **React Router** for routing. TanStack Router is the more type-safe
  alternative, but it's less recognizable to a reviewer skimming the code.
- **Tailwind CSS** with a few small shared components in `src/components/`.
  The app needs about six primitives, so shadcn/ui's CLI and generated files
  weren't worth adding.
- **Vitest + React Testing Library**, which pair natively with Vite.
- **TypeScript 6**, pinned deliberately: TypeScript 7 (the native port)
  doesn't ship the JS compiler API that `openapi-typescript` needs.

No Zustand/Redux: the only cross-page state is the API key (sessionStorage)
and the patient filters, which live in the URL.

## Structure

Feature-based, mirroring the layered `backend/`:

```
dashboard/
  src/
    app/                 # router, layout, sign-in, route pages that compose features
    features/
      patients/          # api/ (query hooks), components/, types.ts, index.ts
      calls/
      stats/
      logs/
    components/          # shared, feature-agnostic UI (Card, Button, Badge, ...)
    lib/                 # API client (envelope unwrapping), API key, formatting
    types/api.d.ts       # generated from the backend's OpenAPI schema
```

**Boundaries.** Each feature exposes its public surface through `index.ts`.
Features never import from each other. When a page needs two features
(patient detail shows the patient and their calls), the composition happens in
`app/routes.tsx`. `components/` and `lib/` never import from `features/`.
This is enforced by convention for now; an ESLint `import/no-restricted-paths`
rule would make it mechanical.

**Generated types, not hand-written duplicates.** `src/types/api.d.ts` is
generated from the backend's OpenAPI schema (`npm run gen:api`), and feature
`types.ts` files alias it (`components["schemas"]["PatientOut"]`). If a
backend model changes, the compiler catches every mismatch here. Re-run
`gen:api` after changing the backend's API models.

## Auth

The REST API needs `X-API-Key`. Standalone (`npm run dev`), the key is
entered on a sign-in screen, checked against the API, and kept only in the
tab's `sessionStorage`. The embedded build the backend serves skips that
screen: the backend asks for the key before serving the page and sets an
HttpOnly session cookie, which same-origin API calls carry instead of the
header. Either way the key is never baked into the bundle.
