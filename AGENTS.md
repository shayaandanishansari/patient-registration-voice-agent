# AGENTS.md

Notes for any agent (human or AI) picking up this repo.

## What this is

A take-home coding challenge from CareCloud: build a voice AI agent for patient
pre-registration. The brief (`docs/CONFIDENTIAL/`, gitignored — candidate-only material)
specifies a registration flow with a patient data model and API spec, and offers
appointment scheduling as an optional bonus.

## Where we are

Backend is built and deployed: Retell tool endpoints, webhook, and read-only REST API
are all implemented, tested against a real Atlas cluster, and live on Railway at
`https://patient-registration-voice-agent-production-f401.up.railway.app`. The
conversation flow has been pushed to Retell (`conversation_flow_0d5801eaa834`) via
`scripts/deploy_retell_flow.py`, and the agent's webhook URL is set to
`<that URL>/retell/webhook`. Dashboard is planned but not scaffolded — see
`dashboard/ARCHITECTURE.md`. Monorepo layout is `backend/` (FastAPI) + `dashboard/`
(TypeScript/React), both at repo root.

Still open before a real phone call should be trusted: Railway's `ALLOW_UNSIGNED_REQUESTS`
is currently `true` (left on from curl testing) — flip it to `false` and confirm
`RETELL_API_KEY` is set on that service before going live, otherwise `/retell/*` accepts
unsigned requests from anyone who finds the URL.

Stack decisions: MongoDB Atlas via Motor (async) for the DB — verified working in
`playground/db_connection/` before being wired into `backend/app/db.py`. Retell AI is
the voice/telephony + LLM layer; the actual conversation flow is designed and tracked
at `backend/retell/conversation_flow.json` (a copy of `playground/retell_api/`'s, which
stays as the original testing-pattern showcase). The flow's tool contract (`create_patient`,
`verify_patient`, `get_patient_profile`, `update_patient_profile` calling
`/retell/tools/*`) is the source of truth for argument names and response shapes — treat
it as fixed; changing a key there breaks the flow's branching silently.

`docs/identity-carecloud-voiceagent.html` is a research memo
that settles what kind of phone line this agent actually is, since the brief itself is
ambiguous (narrow intake line vs. general switchboard). Conclusion, briefly:

- **CareCloud VoiceAgent is a pre-registration and patient access line** — an intake
  coordinator for a patient whose care was already arranged elsewhere (by a referring
  physician), not a general hospital switchboard and not nurse triage.
- It collects demographics/insurance, **verifies identity on at least two identifiers**
  before touching an existing record (HIPAA Security Rule obligation for phone/PHI), reads
  everything back for confirmation, and writes to the patient database.
- The brief's duplicate-detection bonus is implemented as identity verification, not as a
  free lookup-by-phone-number.
- Appointment scheduling (the bonus) is framed as the same coordinator doing an adjacent
  part of the job, not a second persona.
- The call opens with an emergency disclaimer ("if this is life-threatening, hang up and
  dial 911") and the agent explicitly will not do symptom assessment or triage — that's a
  licensed-nurse function behind a clinical/non-clinical boundary, and it hands off instead.

This identity is meant to drive the system prompt's scope, identity-verification approach,
and emergency disclaimer once implementation starts. All of it — the emergency disclaimer,
the registration-only scope, the security rules around verification — is already baked into
`backend/retell/conversation_flow.json`'s `global_prompt`.

Note: `docs/patient_field_spec.xlsx` specifies `patient_id` as a UUID (fine for a REST
resource, unspeakable over the phone). The implemented schema adds `member_id` — 8 random
digits — as the voice-facing verification identifier the xlsx spec didn't anticipate; Mongo's
own `_id` still serves as the storage key. Insurance/emergency-contact fields from the xlsx
are carried on the `patients` schema but not yet collected by the conversation flow (see
`backend/README.md`'s design-decisions section for the full reasoning and known limitations).

## Layout

| Path | What it is | Tracked? |
|---|---|---|
| `docs/identity-carecloud-voiceagent.html` | Design research memo (see above) | Yes |
| `docs/patient_field_spec.xlsx` | Patient data model / field spec | Yes |
| `docs/README.md` | Index of `docs/` | Yes |
| `docs/CONFIDENTIAL/` | Original brief from CareCloud (candidate-use-only) | No (gitignored) |
| `backend/` | FastAPI backend — implemented, see below | Yes |
| `dashboard/ARCHITECTURE.md` | Planned dashboard structure/stack (not built yet) | Yes |
| `playground/` | Scratch/experiment space — intentionally tracked, showcases testing patterns (DB connection, Retell API) | Yes |
| `.idea/` | PyCharm project config — Python 3.14, Black formatter | No (gitignored) |

## Backend (`backend/`)

FastAPI, Python 3.11+ (running on 3.14 locally), no venv — run against the system
interpreter (already has fastapi/pydantic/pytest/motor/retell-sdk/phonenumbers/etc.
installed globally). `app/` layout, feature-grouped by technical concern:

- `app/config.py` — `pydantic-settings`, reads `.env`.
- `app/db.py` — Motor client (`AsyncIOMotorClient`), index creation, thin `Database`
  wrapper exposing `.patients`/`.calls` collections.
- `app/security.py` — `verify_retell_signature` (checks `X-Retell-Signature` via
  `retell-sdk`'s `Retell(...).verify`, honors `ALLOW_UNSIGNED_REQUESTS` for local-only
  debugging) and `require_api_key` (for `/api/*`).
- `app/validation.py` — normalizers for name/DOB/sex/phone/state/ZIP/email/member_id,
  each raising `ValidationError` with a short speakable message. Fully unit tested.
- `app/models.py` — Retell request envelope + Pydantic response shapes for the REST API.
- `app/services/patients.py`, `app/services/calls.py` — the actual registration/
  verification/update logic and the two-collection Mongo access.
- `app/routers/retell_tools.py` — the four tool endpoints (`/retell/tools/*`).
- `app/routers/retell_webhook.py` — `/retell/webhook` (`call_started`/`call_ended`/
  `call_analyzed`, idempotent upsert by `call_id`, never touches verification state).
  Also exposes an unauthenticated `GET /retell/webhook` probe and tolerates an
  empty/malformed POST body as a no-op — added after Retell's dashboard "Test" button
  on the webhook URL turned out to send a plain connectivity check, not a real event.
- `app/routers/api.py` — read-only `/api/*` (patients, calls, health), `X-API-Key`
  protected except `/api/health`.
- `retell/conversation_flow.json` — the fixed tool contract (copied from
  `playground/retell_api/conversation_flow.json`, the original testing-pattern copy).
- `scripts/deploy_retell_flow.py` — pushes the flow to Retell via `retell-sdk`,
  rewriting the placeholder tool URL to `PUBLIC_BASE_URL`.
- `tests/` — `mongomock-motor`-backed; signature/API-key auth, validators, and all four
  tool endpoints (including idempotency and verification-response-shape-parity cases)
  are covered. Run: `python -m pytest -q` from `backend/`.
- `.env.example` is tracked; `.env` is real local config (gitignored), has a working
  Atlas URI and `ALLOW_UNSIGNED_REQUESTS=true` for local curl testing; `RETELL_API_KEY`
  still needs to be filled in from the Retell dashboard before a real signed request or
  a real phone call will work.

See `backend/README.md` for architecture diagram, deploy steps, curl examples, and the
full design-decisions/known-limitations writeup.

## Dashboard (`dashboard/`)

Not scaffolded yet — `dashboard/ARCHITECTURE.md` has the planned stack (Vite + TS +
React, TanStack Query, React Router, Tailwind + shadcn/ui) and feature-based folder
structure (mirrors the backend's approach: group by feature — `patients`, `calls` —
not by technical type). Includes a note to generate API types from the backend's OpenAPI
schema via `openapi-typescript` rather than hand-writing duplicate interfaces.

## Next steps

1. On Railway, set `ALLOW_UNSIGNED_REQUESTS=false` and confirm `RETELL_API_KEY` is set,
   then redeploy — currently still running with signature verification disabled.
2. Confirm the Retell dashboard's webhook connectivity test passes against
   `/retell/webhook` (GET probe + lenient POST added for this — see Backend section).
3. Place a real call: register a patient, call back and verify, hear the record read
   back, update a field, and confirm a wrong DOB ends the call on the security path.
   Confirm the results show up via `/api/patients` and `/api/calls`.
4. Scaffold `dashboard/` per `dashboard/ARCHITECTURE.md`.
