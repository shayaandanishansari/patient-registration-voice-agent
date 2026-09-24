# Hospital VoiceAgent — backend

FastAPI service behind the Retell AI voice agent. It registers new patients,
verifies and updates existing ones, and exposes a
REST API over the same data. See `../README.md` for the live demo details and
`../docs/identity-voiceagent.html` for the design rationale (what
kind of phone line this is, and why verification works the way it does).

## Architecture

```
caller (phone)
   |
   v
Retell AI  -- telephony, speech-to-text, text-to-speech, and the LLM (GPT-4.1)
   |          running the conversation flow in
   |          assets/retell_agent_scripts/agent.json
   |
   +--> POST /retell/tools/check-existing-patient  }
   +--> POST /retell/tools/create-patient          }  tool calls made
   +--> POST /retell/tools/verify-patient          }  during the live call
   +--> POST /retell/tools/get-patient             }  (signed with
   +--> POST /retell/tools/update-patient          }  X-Retell-Signature)
   |
   +--> POST /retell/webhook   call_started / call_ended / call_analyzed
   v
FastAPI (this service)
   routers/   HTTP layer: REST API + Retell tool endpoints + webhook
   services/  business logic, shared by the REST API and the voice tools
   models/    Pydantic request/response models (validation lives here)
   core/      config, database, auth, errors, validation rules, migrations
   |
   v
MongoDB Atlas — collections: patients, calls, logs
   ^
   |
REST API: /patients (CRUD), /calls, /logs, /stats, /health
```

**Separation of concerns.** Retell owns telephony, speech and the LLM, and
the conversation flow decides *what to say*. The backend decides *what is
true*: every value is validated and normalized server-side, whichever channel
it came from. The voice tools and the REST API both go through
`services/patients.py` and the same `PatientCreate`/`PatientUpdate` models, so
there is exactly one implementation of the data rules.

**Why these choices.**
- *Retell AI* — gives us a real phone number, low-latency speech, and a
  node-based conversation flow in one platform. That lets the 3 hours go into
  the prompt, the tools and the backend, not into audio plumbing.
- *FastAPI + Pydantic* — async (tool calls must answer in well under 2s),
  declarative validation, and free OpenAPI docs at `/docs` (the dashboard
  generates its TypeScript types from them).
- *MongoDB Atlas via Motor* — managed and persistent, so it survives restarts
  and redeploys. The document shape maps 1:1 to the patient record. Schema
  rules are enforced by a `$jsonSchema` validator (see Data model).
- *Railway* — deploys from GitHub with a health check, with zero infra to
  manage.

## Data model

`patients` follows `docs/patient_field_spec.xlsx` field for field:

| Field | Stored as | Rule |
|---|---|---|
| `patient_id` | UUID string | Auto. The REST resource ID. |
| `member_id` | 8 digits | Auto. The ID the caller hears and later reads back to verify (a UUID can't be spoken). |
| `first_name`, `last_name` | string | 1–50 chars. Letters, hyphens, apostrophes (plus spaces/periods for names like "Mary Ann", "St. John"). |
| `date_of_birth` | `YYYY-MM-DD` | Accepts MM/DD/YYYY, ISO, or "March 5, 1990". Not in the future, not over 120 years ago. |
| `sex` | enum | `Male`, `Female`, `Other`, `Decline to Answer` |
| `phone_number`, `emergency_contact_phone` | 10 digits | Valid U.S. (NANP) number. Formatting stripped. |
| `email` | string | Valid format (optional) |
| `address_line_1`, `address_line_2`, `city` | string | Line 1 required, city 1–100 chars |
| `state` | 2-letter code | Accepts a code or the full name ("Texas" → `TX`). Includes DC and territories. |
| `zip_code` | string | `12345` or `12345-6789` |
| `insurance_provider`, `insurance_member_id` | string | Optional. The member ID is alphanumeric, with spoken spaces and dashes removed. |
| `preferred_language` | string | Defaults to `English` |
| `emergency_contact_name` | string | Optional full name |
| `created_at`, `updated_at`, `deleted_at` | UTC datetimes | Auto. `deleted_at` is set by soft delete. |

Plus audit metadata: `created_via` (`voice`/`api`), `created_via_call_id`,
and `update_history` (who changed which fields, from which call, and when).

**Enforcement happens twice.** The Pydantic models validate and normalize
first, with short, speakable error messages. At startup,
`core/db_schema.py` also attaches a MongoDB `$jsonSchema` validator
(types, required fields, patterns, enums) as a backstop against writes that
bypass the app. Attaching it needs the `collMod` privilege (Atlas `dbAdmin`);
without that privilege it logs a warning and the app-level rules still apply.

`calls` stores Retell call metadata, the transcript, the post-call analysis,
and links to patients (`patients_created`, `verified_patient_id`).

## REST API

All endpoints except `/health` need an `X-API-Key` header. Every response
uses the same envelope:

```json
{ "data": { ... }, "error": null }
{ "data": null, "error": { "code": "validation_error", "message": "...", "details": [{ "field": "zip_code", "message": "..." }] } }
```

List endpoints add `"meta": { "limit": 20, "next_cursor": "..." }`. Pass
`?cursor=` to get the next page.

| Method | Path | Notes |
|---|---|---|
| GET | `/patients` | Filters: `?last_name=` (case-insensitive), `?date_of_birth=` (either format), `?phone_number=` (any format), `?member_id=`, `?include_deleted=true` |
| GET | `/patients/{patient_id}` | 404 if unknown or soft-deleted, 400 if not a UUID |
| POST | `/patients` | 201 with the created record. 409 if the same person (name + DOB + phone) already exists. |
| PUT | `/patients/{patient_id}` | Partial update: only the fields sent change. `null` clears an optional field. Required fields can't be cleared. |
| DELETE | `/patients/{patient_id}` | Soft delete: sets `deleted_at` and returns the record |
| GET | `/calls`, `/calls/{call_id}` | `?patient_id=` lists the calls that registered or verified a patient |
| GET | `/health` | No auth. Checks the database connection. |
| GET | `/dashboard` | The web dashboard (pre-built from `../dashboard`, committed in `assets/dashboard/`). Needs the key: the browser asks for a login (any username, the API key as password), then a session cookie covers the dashboard's API calls. |

Status codes: `200` OK, `201` created, `400` malformed request (bad JSON,
bad query parameter, bad cursor, non-UUID ID, empty update), `401` missing
or invalid key, `404` not found, `409` duplicate, `422` field validation
failed, `500` unexpected error (still enveloped, and logged with a stack
trace). Unknown body fields are rejected with 422, and every string goes
through its field's normalizer before it touches the database.

```bash
export BASE=https://patient-registration-voice-agent-production-f401.up.railway.app
export KEY=...   # API_KEY

curl "$BASE/patients?last_name=doe" -H "x-api-key: $KEY"
curl -X POST "$BASE/patients" -H "x-api-key: $KEY" -H "content-type: application/json" -d '{
  "first_name": "Jane", "last_name": "Doe", "date_of_birth": "03/05/1990",
  "sex": "Female", "phone_number": "(512) 555-0123",
  "address_line_1": "123 Main St", "city": "Austin", "state": "TX", "zip_code": "78701"
}'
curl -X PUT "$BASE/patients/<patient_id>" -H "x-api-key: $KEY" -H "content-type: application/json" -d '{"city": "Round Rock"}'
curl -X DELETE "$BASE/patients/<patient_id>" -H "x-api-key: $KEY"
```

Interactive docs: `$BASE/docs`. The browser asks for a login: any username, the API key as
password. `/openapi.json` also takes the `X-API-Key` header.

## The voice agent

The full agent is `assets/retell_agent_scripts/agent.json`. It's a
Retell agent export that you can import in the Retell dashboard. Its
`global_prompt` is the system message, and each node's `instruction` is
that step's prompt.

### Conversation flow

```
welcome (emergency/911 disclaimer, "register, check/update, or book?")
 ├─ register ─> reg_collect_identity (name spelled, DOB, sex, phone)
 │               └─> check_existing_patient
 │                    ├─ existing ─> reg_existing: "It looks like we already have a
 │                    │              record for Jane Doe. Would you like to update
 │                    │              your information instead?" ─> verify_collect
 │                    ├─ invalid ──> reg_fix_identity (re-ask that one field)
 │                    └─ none ─────> reg_collect_details (address, email, then offers
 │                                   insurance / emergency contact / language)
 │                                   ─> full read-back ─> caller confirms
 │                                   ─> create_patient
 │                                        ├─ created ─> reg_success ("You're all set, Jane",
 │                                        │             member ID read in groups)
 │                                        ├─ invalid ─> reg_fix (re-ask that one field)
 │                                        ├─ duplicate ─> reg_existing
 │                                        └─ error/timeout ─> system_error (spoken apology)
 ├─ check/update ─> verify_collect (member ID + full name + DOB) ─> verify_patient
 │                   ├─ verified ─> manage_profile (read back / update)
 │                   └─ not verified ─> verify_failed (ends call, reveals nothing)
 ├─ forgot member ID ─> forgot_member_id (in person with photo ID, or register)
 └─ start_over (global node: reachable from anywhere)
```

### Prompt design, and why

- **One identity and scope in the global prompt.** Sarah is a registration
  coordinator, not a clinician. That keeps the agent out of triage. The 911
  disclaimer is part of the greeting itself, not left to the model's
  judgement.
- **Collect in two phases.** Identity and phone come first, so the
  duplicate check runs *before* the caller spends two minutes on their
  address. It also lets an invalid DOB or a 3-digit phone number be
  re-asked right away.
- **Out-of-order answers and corrections are handled in the prompt.** "Accept
  whatever they give, keep it, only ask for what is still missing." A
  correction replaces the value and is confirmed on its own. The final
  read-back covers every field before anything is saved.
- **Voice-specific formatting rules.** Names and emails are spelled out,
  numbers read digit by digit in groups, dates spoken as words. The model
  never reads lists or formatting aloud.
- **The backend never trusts the LLM with identity.** After verification,
  `get-patient`/`update-patient` resolve the patient
  from Retell's `call_id` on the server. No tool accepts a patient ID from
  the model, so a confused or prompt-injected model can't reach another
  record.
- **Validation messages are written to be spoken.** Every backend validation
  error is one short sentence the agent can say as-is ("The date of birth
  can't be in the future."). The flow's fix-up nodes re-ask only the failing
  field.
- **Spanish.** The agent language is `["en-US", "es-419"]`. On "Hablo
  español" the prompt switches the rest of the call, read-backs included,
  to Spanish, while tool arguments keep their canonical formats.

## Edge cases

| Scenario | What happens |
|---|---|
| Invalid DOB / 3-digit phone | The server rejects it with a speakable reason. The flow re-asks only that field (at the identity step, or `reg_fix` after the read-back). |
| Caller corrects a field ("D-A-V-I-S, not D-A-V-I-E-S") | The prompt replaces the value and confirms just that field. The full read-back before saving catches anything missed. |
| Caller wants to start over | Global `start_over` node, reachable from any point. Unsaved details are discarded. If a record was already saved, the agent says so. |
| Database write fails | The tool returns HTTP 500 and Retell takes the else-edge to `system_error`, which apologizes and ends the call. There is never silence (see `test_db_failure_returns_error_not_silence`). |
| Tool call retried by Retell | `create-patient` is idempotent per call + name + DOB. Updates are naturally idempotent. |
| Call drops mid-registration | Nothing is written until the caller confirms the read-back, so there are no half-records. The webhook still records the call, its transcript and its `disconnection_reason`. On the next call they start over, and if they had finished, the duplicate check recognizes them. |
| Returning caller registers again | The duplicate check (phone + name + DOB) offers to update instead. |
| Household sharing one phone | A phone match alone isn't treated as a duplicate: a household member with a different name or DOB registers normally. |
| Wrong verification details | One generic failure message, then the call ends. Which detail was wrong is never revealed. Soft-deleted patients can't verify. |

## Observability

Structured log lines go to stdout (Railway's log view):
`patient_created ... payload={...}` / `patient_updated ... payload={...}` with
the final collected data, one `tool=... status=...` line per tool call, and
the full transcript (`call_transcript`) and summary (`call_summary`) from
the webhook. Transcripts are also stored on the `calls` document, linked to
the patient.

## Running locally

```bash
cd backend
python -m pip install -e ".[dev]"
cp .env.example .env   # fill in MONGODB_URI, API_KEY, RETELL_API_KEY
python -m uvicorn app.main:app --reload
python -m pytest -q    # mongomock-motor, no real database needed
```

## Environment variables

| Variable | Purpose |
|---|---|
| `MONGODB_URI` | Atlas connection string |
| `MONGODB_DB` | Database name (default `patient_registration`) |
| `API_KEY` | Required `X-API-Key` for the REST API, dashboard and docs |
| `RETELL_API_KEY` | The Retell key used to verify `X-Retell-Signature` |
| `ALLOW_UNSIGNED_REQUESTS` | `true` only for local curl testing. Never in production. |
| `PUBLIC_BASE_URL` | This deployment's URL (informational) |
| `CORS_ORIGINS` | JSON array of allowed origins (the dashboard) |
| `LOG_LEVEL` | Default `INFO` |

## Deploying

1. **Atlas**: allow Railway's egress under Network Access.
2. **Railway**: root directory `backend/`, and set the variables above.
   `railway.json` supplies the start command and the `/health` check. On
   startup the app upgrades any records from the first backend version
   (`core/migrations.py`, idempotent), creates indexes, and attaches the
   schema validator.
3. **Retell**: import `assets/retell_agent_scripts/agent.json` (its
   tool URLs already point at the Railway deployment). Set the agent's
   webhook URL to `<base>/retell/webhook` and assign the phone number.

## Known limitations and trade-offs

- **PHI in logs.** The collected payload and transcripts are logged because
  the brief asks for it. That's fine for test data, but production would
  redact it.
- **Verification uses exact matching** (case-insensitive), with no fuzzy name
  matching. There's no lockout across calls after repeated failed
  verification, and no human escalation path.
- **No scheduling.** The line handles registration only; callers who ask
  about appointments are sent to the front desk. A mock scheduling backend
  is kept on the `feature/appointment-scheduling` branch.
- **One shared API key**, not per-user auth or roles.
- **Duplicate detection needs name + DOB + phone together.** A patient who
  changed their phone number won't be caught; a person merges those records
  in person.
- **Atlas Network Access** is open (0.0.0.0/0) for deploy convenience.
  Production would allowlist Railway's egress.

## Next steps

- A lockout or escalation to a human after N failed verifications across calls.
- Per-user dashboard auth, and PHI redaction in logs.
- Scheduling as its own line or agent, backed by a provider calendar.
- Fuzzy name matching for verification and duplicates (e.g. "Jon" vs "John").
