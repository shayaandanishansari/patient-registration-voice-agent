# Hospital VoiceAgent — dashboard

A simple web UI over the patient database: search patients, open a record
(demographics, insurance, edit history, calls), and read
each call's transcript and summary. Read-only; all writes go through the
voice agent or the REST API.

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

See `ARCHITECTURE.md` for the structure and the reasoning behind it.
