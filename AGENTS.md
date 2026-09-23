# AGENTS.md

Notes for any agent (human or AI) picking up this repo.

## What this is

A take-home coding challenge from CareCloud: build a voice AI agent for patient
pre-registration. The brief (`docs/CONFIDENTIAL/`, gitignored — candidate-only material)
specifies a registration flow with a patient data model and API spec, and offers
appointment scheduling as an optional bonus.

## Where we are

Backend is scaffolded (structure only, no registration-flow logic yet). Dashboard is
planned but not scaffolded — see `dashboard/ARCHITECTURE.md`. Monorepo layout is
`backend/` (FastAPI) + `dashboard/` (TypeScript/React), both at repo root.

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
and emergency disclaimer once implementation starts.

## Layout

| Path | What it is | Tracked? |
|---|---|---|
| `docs/identity-carecloud-voiceagent.html` | Design research memo (see above) | Yes |
| `docs/patient_field_spec.xlsx` | Patient data model / field spec | Yes |
| `docs/README.md` | Index of `docs/` | Yes |
| `docs/CONFIDENTIAL/` | Original brief from CareCloud (candidate-use-only) | No (gitignored) |
| `backend/` | FastAPI backend — scaffolded, see below | Yes |
| `dashboard/ARCHITECTURE.md` | Planned dashboard structure/stack (not built yet) | Yes |
| `playground/` | Scratch/experiment space | No (gitignored) |
| `.idea/` | PyCharm project config — Python 3.14, Black formatter | No (gitignored) |

## Backend (`backend/`)

FastAPI, Python 3.14, no venv — run against the system interpreter (already has
fastapi/pydantic/pytest/etc. installed globally). `src/` layout, feature-grouped by
technical concern rather than a nested package name (`src/models`, `src/routes`,
`src/services`, `src/config.py`, `src/deps.py`, `src/main.py`).

- `models/patient.py`, `models/call.py` — pydantic models generated directly from
  `docs/patient_field_spec.xlsx` (`Patients` and `Calls` sheets), including field
  validation rules from that spec (name/phone/zip/state formats, DOB not in future, etc).
- `routes/health.py` — only endpoint that exists so far (`GET /health`).
- `services/` — intentionally empty. This is where the registration flow (identity
  verification, read-back confirmation) belongs once the LLM/telephony stack is picked.
- No `db.py` yet — deliberately deferred until a DB is chosen.
- `.env.example` is tracked; `.env` is real local config (gitignored) and already exists
  locally with dev defaults.
- Run tests: `python -m pytest -q` from `backend/`.

## Dashboard (`dashboard/`)

Not scaffolded yet — `dashboard/ARCHITECTURE.md` has the planned stack (Vite + TS +
React, TanStack Query, React Router, Tailwind + shadcn/ui) and feature-based folder
structure (mirrors the backend's approach: group by feature — `patients`, `calls` —
not by technical type). Includes a note to generate API types from the backend's OpenAPI
schema via `openapi-typescript` rather than hand-writing duplicate interfaces.

## Next steps

1. Pick the voice/telephony + LLM stack and the DB.
2. Build `services/registration.py` (identity verification, read-back confirmation) and
   the `/patients` + `/calls` routes against it, per the identity in this file.
3. Scaffold `dashboard/` per `dashboard/ARCHITECTURE.md`.
