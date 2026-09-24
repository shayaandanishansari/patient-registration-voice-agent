# AGENTS.md

Notes for any agent (human or AI) picking up this repo.

## What this is

A take-home coding challenge from CareCloud: build a voice AI agent for patient
pre-registration. The brief (`docs/CONFIDENTIAL/`, gitignored — candidate-only material)
specifies a registration flow, a patient data model, a REST API (full CRUD on `/patients`
with a `{data, error}` envelope and soft delete), and bonuses (duplicate detection,
appointment scheduling, Spanish, transcripts, dashboard, tests). All of it is implemented;
see the root `README.md` for the reviewer-facing summary.

## Where we are

Backend, agent flow and dashboard are built. The backend is deployed on Railway at
`https://patient-registration-voice-agent-production-f401.up.railway.app`, but **the
latest changes (REST CRUD at `/patients`, the new flow, scheduling) are not deployed yet**.
To go live:

1. Deploy the backend. On startup it migrates records written by the first version
   (`app/core/migrations.py`, idempotent), creates indexes, and attaches the patients
   `$jsonSchema` validator (needs Atlas `dbAdmin`; it logs a warning otherwise).
2. Re-import `backend/assets/retell_agent_scripts/agent.json` into Retell. Its tool
   URLs already point at the Railway URL. The agent language is `["en-US", "es-419"]`.
   There is no upload script; import it through the Retell dashboard.
3. On Railway: `ALLOW_UNSIGNED_REQUESTS=false`, `RETELL_API_KEY` set, and `API_KEY` set
   (`API_READ_KEY` still works as an alias). Healthcheck path is now `/health`.
4. Put the Retell phone number into the root `README.md` (marked TODO).

Stack decisions: MongoDB Atlas via Motor (async), verified in `playground/db_connection/`.
Retell AI is the voice/telephony + LLM layer. The agent (global prompt, nodes, tools) lives
in `backend/assets/retell_agent_scripts/agent.json`, a Retell agent export and the
source of truth for the flow. `playground/retell_api/` keeps the earlier versions.
`tests/test_flow_contract.py` checks that the flow's tool URLs, argument names, response
variables and equation-edge values match the backend. Run it after editing either side,
because a mismatch fails silently on a live call (the flow just takes its else-edge).

`docs/identity-carecloud-voiceagent.html` is a research memo that settles what kind of
phone line this is. Briefly:

- **A pre-registration and patient access line**: an intake coordinator, not a hospital
  switchboard and not nurse triage. No symptom assessment; it hands off instead.
- **Identity is verified on member ID + full name + DOB** before touching an existing
  record, and post-verification access is bound server-side to Retell's `call_id`.
- **Duplicate detection** (the brief's bonus) matches on phone + name + DOB together.
  Phone alone isn't identity (households share lines), so the agent only ever says back a
  name the caller just gave. It then offers to update via verification.
- **Scheduling** is the same coordinator doing an adjacent task (first appointment only),
  bound to the patient registered or verified on the call.
- The call opens with the 911 emergency disclaimer.

`docs/patient_field_spec.xlsx` specifies `patient_id` as a UUID, which is the REST resource
ID. `member_id` (8 random digits) is the voice-facing ID the caller reads back to verify.

## Layout

| Path | What it is | Tracked? |
|---|---|---|
| `README.md` | Reviewer-facing overview, live demo details, stack justification | Yes |
| `docs/` | Field spec, identity memo, index | Yes |
| `docs/CONFIDENTIAL/` | Original brief (candidate-use-only) | No (gitignored) |
| `backend/` | FastAPI backend + Retell agent export | Yes |
| `dashboard/` | Vite/React dashboard over the REST API | Yes |
| `playground/` | Experiments kept as a showcase of testing patterns | Yes |
| `.idea/` | PyCharm config — Python 3.14, Black | No |

## Backend (`backend/`)

FastAPI, Python 3.11+ (3.14 locally), no venv; the system interpreter has the
dependencies installed. Layered layout:

- `app/main.py` — app factory, lifespan (migrate → indexes → schema validator), exception
  handlers, routers.
- `app/core/` — shared infrastructure: `config.py` (pydantic-settings), `database.py`
  (Motor client, `Database` wrapper with `patients`/`calls`/`appointments` and all indexes,
  `DbDep`), `db_schema.py` (patients `$jsonSchema`), `migrations.py` (legacy record
  upgrade), `security.py` (Retell signature + `X-API-Key`), `errors.py` (envelope error
  handlers: 400/401/404/409/422/500), `pagination.py` (cursor paging), `validation.py`
  (field normalizers with short speakable error messages).
- `app/models/` — Pydantic models. `patients.py` has `PatientCreate`/`PatientUpdate`,
  whose validators call `core/validation.py`. These are used by **both** the REST API and
  the voice tools, so the rules exist once. `common.py` has the `Envelope`/`ListEnvelope`
  response wrappers.
- `app/services/` — business logic. `patients.py` (create with duplicate check +
  idempotency, verify, update with `update_history`, soft delete, payload logging),
  `calls.py` (per-call verification/registration state), `appointments.py` (mock slots,
  booking).
- `app/routers/` — `patients.py` (CRUD), `calls.py`, `appointments.py`, `health.py`,
  `retell_tools.py` (7 tool endpoints under `/retell/tools/*`), `retell_webhook.py`
  (idempotent upsert by `call_id`, logs transcript/summary, never touches verification
  state; tolerates Retell's connectivity-test GET/empty POST).
- `assets/retell_agent_scripts/agent.json` — the Retell agent.
- `tests/` — `mongomock-motor`-backed, no real DB. Run `python -m pytest -q` from
  `backend/`.

## Dashboard (`dashboard/`)

Vite + React + TS, TanStack Query, React Router, Tailwind. Feature folders (`patients`,
`calls`, `appointments`) that never import each other; cross-feature pages are composed
in `src/app/routes.tsx`. API types are generated from the backend's OpenAPI
(`npm run gen:api`). TypeScript is pinned to 6.x because TS 7 lacks the compiler API
`openapi-typescript` needs. See `dashboard/ARCHITECTURE.md`.

The backend also serves the dashboard at `/dashboard` (`app/routers/dashboard.py`)
from a pre-built copy committed in `backend/assets/dashboard/`, because Railway only
builds Python. After changing the dashboard, run `npm run build:backend` in
`dashboard/` and commit the output. That build mode blanks `VITE_API_KEY`, so a local
key never ships in the public bundle.
