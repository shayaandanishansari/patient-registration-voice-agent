# AGENTS.md

Notes for any agent (human or AI) picking up this repo.

## What this is

A take-home coding challenge: build a voice AI agent for patient
pre-registration. The brief (`docs/CONFIDENTIAL/`, gitignored — candidate-only material)
specifies a registration flow, a patient data model, a REST API (full CRUD on `/patients`
with a `{data, error}` envelope and soft delete), and bonuses (duplicate detection,
appointment scheduling, Spanish, transcripts, dashboard, tests). The core brief, transcripts,
dashboard and tests are done. Returning callers verify and update instead of re-registering,
and the agent runs in 12 locales (Spanish included). Scheduling is deliberately out of
scope: it was removed from `main` and kept on the `feature/appointment-scheduling` branch.
See the root `README.md` (Bonus challenges) for the reviewer-facing summary.

## Where we are

Backend, agent flow and dashboard are built, and the backend is deployed on Railway at
`https://patient-registration-voice-agent-production-f401.up.railway.app` (auto-deploys
from `main`). The remaining steps before submitting are in the root `TODO.md`.

- **Railway variables** come from `backend/.env.production` (gitignored), pasted into the
  service's Raw Editor. Never paste the local `backend/.env` (development values). Needed:
  `ENVIRONMENT=production`, `ALLOW_UNSIGNED_REQUESTS=false` (the app refuses to start on
  Railway otherwise), `API_KEY`, and `RETELL_API_KEY` = the Retell key with the webhook
  badge. Healthcheck path is `/health`.
- **Retell agent:** import `backend/assets/retell_agent_scripts/agent.json` through the
  Retell dashboard (there is no upload script). Its tool URLs already point at the Railway
  URL. Set the agent's webhook URL to `/retell/webhook` there.
- On startup the backend migrates records written by the first version
  (`app/core/migrations.py`, idempotent), creates indexes, and attaches the patients
  `$jsonSchema` validator (needs Atlas `dbAdmin`; it logs a warning otherwise).

Stack decisions: MongoDB Atlas via Motor (async), verified in `playground/db_connection/`.
Retell AI is the voice/telephony + LLM layer (the flow runs on Claude Sonnet 5). The agent
(global prompt, nodes, tools) lives in `backend/assets/retell_agent_scripts/agent.json`, a
Retell agent export and the source of truth for the flow. The flow uses 4 tools:
`create_patient`, `verify_patient`, `get_patient_profile`, `update_patient_profile`. `playground/retell_api/` keeps the earlier versions.
`tests/test_flow_contract.py` checks that the flow's tool URLs, argument names, response
variables and equation-edge values match the backend. Run it after editing either side,
because a mismatch fails silently on a live call (the flow just takes its else-edge).

`docs/identity-voiceagent.html` is a research memo that settles what kind of
phone line this is. Briefly:

- **A pre-registration and patient access line**: an intake coordinator, not a hospital
  switchboard and not nurse triage. No symptom assessment; it hands off instead.
- **Identity is verified on member ID + full name + DOB** before touching an existing
  record, and post-verification access is bound server-side to Retell's `call_id`.
- **Duplicate detection** (the brief's bonus) matches on phone + name + DOB together.
  Phone alone isn't identity (households share lines). REST refuses a duplicate (409).
  Voice saves it as a new record and never mentions the match, because that would
  confirm a record to an unverified caller. Staff see it on the dashboard (Overview
  tile, patient page, `?possible_duplicates=true`), computed on read, not stored. Don't
  "fix" this by making voice refuse duplicates or tell the caller.
- **Scheduling** is out of scope for this line: callers are sent to the front desk. A mock
  scheduling backend lives on the `feature/appointment-scheduling` branch, not on `main`.
- A caller who describes a medical emergency is told to hang up and call 911 (scope rule
  in the global prompt; there is no opening disclaimer).

Other docs: `docs/design-decisions.md` (the judgment calls, and where the build departs from
the brief), `docs/api-routes.md` (every route with its auth, kept in step with the app by
`tests/test_api_routes_doc.py`, so update it when you add or change a route), and
`docs/System Architecture.svg` (from the `.excalidraw` next to it). `docs/archive/` is
gitignored drafts.

`docs/patient_field_spec.xlsx` specifies `patient_id` as a UUID, which is the REST resource
ID. `member_id` (8 random digits) is the voice-facing ID the caller reads back to verify.

## Layout

| Path | What it is | Tracked? |
|---|---|---|
| `README.md` | Reviewer-facing overview, live demo details, stack justification | Yes |
| `docs/` | Field spec, identity memo, security review (`security.md`), index | Yes |
| `docs/CONFIDENTIAL/` | Original brief (candidate-use-only) | No (gitignored) |
| `backend/` | FastAPI backend + Retell agent export | Yes |
| `dashboard/` | Vite/React dashboard over the REST API | Yes |
| `playground/` | Experiments kept as a showcase of testing patterns | Yes |
| `TODO.md` | Remaining steps before submitting, in order | Yes |
| `.idea/` | PyCharm config — Python 3.14, Black | No |

## Backend (`backend/`)

FastAPI, Python 3.11+ (3.14 locally), no venv; the system interpreter has the
dependencies installed. Layered layout:

- `app/main.py` — app factory, lifespan (migrate → indexes → schema validator), exception
  handlers, routers.
- `app/core/` — shared infrastructure: `config.py` (pydantic-settings), `database.py`
  (Motor client, `Database` wrapper with `patients`/`calls`/`logs` and all indexes,
  `DbDep`), `db_schema.py` (patients `$jsonSchema`), `migrations.py` (legacy record
  upgrade), `security.py` (Retell signature, API key, and the browser login + session
  cookie for `/dashboard` and `/docs`; see `docs/security.md`), `errors.py` (envelope error
  handlers: 400/401/404/409/422/500), `pagination.py` (cursor paging), `validation.py`
  (field normalizers with short speakable error messages; names accept any script and
  go through `clean_name_text` before storing or comparing, and `db_schema.py`'s name
  pattern must stay in step with it), `logger.py` (structured
  logging; see below).
- Logging: modules log through `EventLogger("app.x").info("event_name", **fields)`, not
  bare `logging`. Each event prints one line to stdout (the brief's observability
  requirement) and is batched into the `logs` collection by `MongoLogHandler`
  (installed in the lifespan; 90-day TTL, `LOG_RETENTION_DAYS` in `database.py`).
  `RequestLogMiddleware` logs an `http_request` event per request and stamps a
  `request_id` (also the `X-Request-ID` response header) on every record. A Mongo
  failure only drops log records; it never fails a request.
- `app/models/` — Pydantic models. `patients.py` has `PatientCreate`/`PatientUpdate`,
  whose validators call `core/validation.py`. These are used by **both** the REST API and
  the voice tools, so the rules exist once. `common.py` has the `Envelope`/`ListEnvelope`
  response wrappers.
- `app/services/` — business logic. `patients.py` (create with duplicate check +
  idempotency, verify, update with `update_history`, soft delete, payload logging),
  `calls.py` (per-call verification/registration state).
- `app/routers/` — `patients.py` (CRUD), `calls.py`, `logs.py`
  (read the `logs` collection by time range, level, event, call), `stats.py`
  (headline counts for the dashboard homepage), `health.py`,
  `retell_tools.py` (the 4 tool endpoints under `/retell/tools/*` the flow calls; its
  route class logs each call's args and response once),
  `retell_webhook.py` (idempotent upsert by `call_id`, logs the full body, never
  touches verification state; its GET probe is the only public route besides `/health`),
  `docs.py` (`/docs`, `/redoc`, `/openapi.json` behind the key), `dashboard.py`.
- Security rule: every route except `/health` and the webhook probe needs the API key or a
  Retell signature. `tests/test_security.py` sweeps all routes and fails on any that
  doesn't return `401` anonymously, so a new route must be protected (or deliberately
  added to its public list).
- `assets/retell_agent_scripts/agent.json` — the Retell agent.
- `tests/` — `mongomock-motor`-backed, no real DB. Run `python -m pytest -q` from
  `backend/`.

## Dashboard (`dashboard/`)

Vite + React + TS, TanStack Query, React Router, Tailwind. Feature folders (`patients`,
`calls`, `logs`, `stats`, `docs`) that never import each other; cross-feature pages
(including the Overview homepage at `/`) are composed in `src/app/routes.tsx`. API types are generated from the backend's OpenAPI
(`npm run gen:api`). TypeScript is pinned to 6.x because TS 7 lacks the compiler API
`openapi-typescript` needs, which also means `npm install <pkg>` needs `--force`
(`--legacy-peer-deps` drops `@testing-library/dom` from the lockfile). The Docs page
(`features/docs`) bundles chosen files from `../docs` and reads the Retell agent export at
build time, so rebuild after editing either. See `dashboard/README.md`.

The backend also serves the dashboard at `/dashboard` (`app/routers/dashboard.py`)
from a pre-built copy committed in `backend/assets/dashboard/`, because Railway only
builds Python. After changing the dashboard, run `npm run build:backend` in
`dashboard/` and commit the output. That build mode blanks `VITE_API_KEY`, so a local
key never ships in the public bundle, and skips the in-app sign-in: the backend asks for
the key (browser login, any username) before serving the page and sets a session cookie
the dashboard's API calls use. `npm run gen:api` needs the key in `API_KEY`
(`dashboard/redocly.yaml` sends it).
