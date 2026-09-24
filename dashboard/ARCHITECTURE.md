# Dashboard architecture

Read-only web UI over the backend's REST API: patients (with filters),
patient detail (demographics, insurance, edit history, appointments, calls),
calls (transcript, summary, recording), and logs (everything Retell sent
and the backend did, filterable by time range, level, event and call). Mirrors the feature-based
approach used for `backend/`.

## Stack

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

```
dashboard/
  src/
    app/                 # router, layout, sign-in, route pages that compose features
    features/
      patients/          # api/ (query hooks), components/, types.ts, index.ts
      calls/
      appointments/
      logs/
    components/          # shared, feature-agnostic UI (Card, Button, Badge, ...)
    lib/                 # API client (envelope unwrapping), API key, formatting
    types/api.d.ts       # generated from the backend's OpenAPI schema
```

**Boundaries.** Each feature exposes its public surface through `index.ts`.
Features never import from each other. When a page needs two features
(patient detail shows calls and appointments), the composition happens in
`app/routes.tsx`. `components/` and `lib/` never import from `features/`.
This is enforced by convention for now; an ESLint `import/no-restricted-paths`
rule would make it mechanical.

## Generated types, not hand-written duplicates

`src/types/api.d.ts` is generated from the backend's OpenAPI schema
(`npm run gen:api`), and feature `types.ts` files alias it
(`components["schemas"]["PatientOut"]`). If a backend model changes, the
compiler catches every mismatch here. Re-run `gen:api` after changing the
backend's API models.

## Auth

The REST API needs `X-API-Key`. Standalone (`npm run dev`), the key is
entered on a sign-in screen, checked against the API, and kept only in the
tab's `sessionStorage`. The embedded build the backend serves skips that
screen: the backend asks for the key before serving the page and sets an
HttpOnly session cookie, which same-origin API calls carry instead of the
header. Either way the key is never baked into the bundle.
