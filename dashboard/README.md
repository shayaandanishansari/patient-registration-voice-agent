# CareCloud VoiceAgent — dashboard

A simple web UI over the patient database: search patients, open a record
(demographics, insurance, edit history, booked appointments, calls), and read
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
- `VITE_API_KEY` is the backend's `API_KEY` (`API_READ_KEY`). When it's set,
  there's no sign-in screen. Leave it unset on any publicly hosted build,
  because `VITE_*` values are compiled into the JavaScript. Without it, the
  dashboard asks for the key and keeps it only for the browser tab.

The backend must allow the dashboard's origin in `CORS_ORIGINS`
(`http://localhost:5173` is allowed by default).

| Script | |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` | Typecheck + production build to `dist/` |
| `npm test` | Vitest |
| `npm run gen:api` | Regenerate `src/types/api.d.ts` from the backend's `/openapi.json` |

See `ARCHITECTURE.md` for the structure and the reasoning behind it.
