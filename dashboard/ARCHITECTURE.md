# Dashboard architecture (planned, not built yet)

Notes from design discussion before the dashboard is scaffolded. Mirrors the
feature-based approach used for `backend/`.

## Stack

- **Vite + TypeScript** — internal SPA hitting the FastAPI backend, no SEO/SSR
  need, so no Next.js.
- **TanStack Query** for all server state (fetching patients/calls, caching,
  loading/error states). Don't hand-roll fetch/useEffect data logic.
- **React Router v7** for routing. TanStack Router is the more type-safe
  alternative (route params compiler-checked) but less recognizable to a
  reviewer skimming the code — default to React Router unless the stricter
  typing becomes worth it.
- **Zustand** only if cross-page client state is actually needed (e.g. a
  filter shared between the calls list and a detail view). Don't reach for
  Redux — this app doesn't have the state complexity to justify it.
- **Tailwind + shadcn/ui** for styling/components — current default for
  admin/data dashboards (tables, forms, detail panels).
- **Vitest + React Testing Library** — pairs natively with Vite.

## Structure

Scoped to what this dashboard actually needs (patients, calls, maybe
appointments for the scheduling bonus) — not a hypothetical enterprise app.

```
dashboard/
  src/
    app/                # routes, root layout, providers (QueryClient, router)
    features/
      patients/
        api/            # TanStack Query hooks calling the backend
        components/
        types.ts
      calls/
        api/
        components/
        types.ts
    components/         # shared, feature-agnostic UI (Table, Button, ...)
    lib/                 # api client instance, query client config
    types/               # generated API types (see below)
  index.html
  package.json
  vite.config.ts
```

## Generated types, not hand-written duplicates

The backend is FastAPI, which produces a free OpenAPI schema. Generate
`src/types/api.d.ts` from it with `openapi-typescript` instead of hand-writing
`Patient`/`Call` interfaces that would silently drift from the backend's
pydantic models whenever either side changes. No shared `packages/` directory
needed — just generate on build.

## Boundary enforcement

Add an ESLint `import/no-restricted-paths` rule (same idea as Bulletproof
React) so:

- `features/patients` cannot import directly from `features/calls`
- `components/` and `lib/` can never import from `features/`

Cheap to set up now, prevents tangled cross-feature imports once the app
grows past two features.

## Sources

- https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md
- https://www.robinwieruch.de/react-folder-structure/
- https://devtoolbox.blog/tanstack-router-vs-react-router-v7-2026/
- https://tanstack.com/start/latest/docs/framework/react/overview
