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
Retell AI  -- telephony, speech-to-text, text-to-speech, and the LLM (Claude Sonnet 5)
   |          running the conversation flow in
   |          assets/retell_agent_scripts/agent.json
   |
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

## Architecture decisions

**Stack.**
- *Retell AI* — gives us a real phone number, low-latency speech, and a
  node-based conversation flow in one platform. That lets the effort go into
  the prompt, the tools and the backend, not into audio plumbing.
- *Claude Sonnet 5 (through Retell)* — strong instruction-following and tool
  calling at conversational latency, which matters for the spelling,
  read-back and security rules.
- *FastAPI + Pydantic* — async (tool calls must answer in well under 2s),
  declarative validation, and free OpenAPI docs at `/docs` (the dashboard
  generates its TypeScript types from them).
- *MongoDB Atlas via Motor* — managed and persistent, so it survives restarts
  and redeploys. The document shape maps 1:1 to the patient record. Schema
  rules are enforced by a `$jsonSchema` validator (see Data model).
- *Railway* — deploys from GitHub with a health check, with zero infra to
  manage.

**The flow decides what to say; the backend decides what is true.** Retell
owns telephony, speech and the LLM. Every value is validated and normalized
server-side, whichever channel it came from. The voice tools and the REST API
both go through `services/patients.py` and the same
`PatientCreate`/`PatientUpdate` models, so there is exactly one
implementation of the data rules.

**Layers.** `routers/` only speaks HTTP, `services/` holds the business
logic, `models/` the Pydantic request/response shapes, and `core/` the
shared infrastructure (config, database, security, errors, validation,
logging, pagination, migrations). Every write and every patient rule goes
through a service function, whichever endpoint calls it. Read-only lists
and stats query the collections directly, since there's no rule to share.

**Duplicates: the REST API refuses them, the phone line registers them
silently.** Identity on the phone is member ID + full name + DOB. Name, DOB and
phone can be known by someone else, so telling a caller "you're already
registered" would confirm that a record exists to a person who hasn't
verified. Voice therefore saves a new record without mentioning the match,
which is what the flow promises a caller who lost their member ID ("any
duplicate is merged in person"). The match is logged and surfaced to staff:
`GET /patients/{id}/duplicates`, `?possible_duplicates=true` and a count in
`/stats`. It's computed from the data rather than stored, so it's never
stale. `POST /patients` refuses with `409`, because its callers are trusted
and should update the existing record. Rationale in
[`../docs/identity-voiceagent.html`](../docs/identity-voiceagent.html); the
code is in `services/patients.py`.

**Identity is bound to the call, not to the model.** Verification records
the patient against Retell's `call_id` on the server. `get-patient` and
`update-patient` look the patient up from that, and no tool takes a patient
ID from the LLM. A confused or prompt-injected model can't reach another
record.

**Two IDs.** `patient_id` is a UUID, the REST resource ID from the field
spec. `member_id` is 8 random digits, because a caller has to read it back
over the phone.

**Tool responses are shaped for the flow.** Tools answer HTTP 200 with a
small `status` the flow branches on (`created`, `invalid`, `verified`, ...)
and a `message` the agent can say as-is. A real failure is an HTTP 500,
which sends the flow to its else-edge and a spoken apology, never silence.

**Safe to retry.** `create-patient` is idempotent per call + name + DOB, so
a Retell retry returns the same record instead of a second one. Updates are
naturally idempotent, and the webhook upserts by `call_id`.

**Nothing is lost.** Patients are soft-deleted (`deleted_at`), and every
update appends to `update_history` (which fields, from which call, when).

**Lists page by cursor**, not offset: the cursor is the last document's
`_id`, so pages stay stable while calls keep adding records.

**Everything needs a credential.** Every route except `/health` and the
webhook reachability probe needs the API key or a Retell HMAC signature,
and `tests/test_security.py` sweeps all routes to enforce it. Details in
[`../docs/security.md`](../docs/security.md).

**Logs go to stdout and to MongoDB.** Stdout is Railway's log view; the
`logs` collection makes them searchable from `GET /logs` and the dashboard
without another service (see Observability). In production they would go
to a log platform instead.

**The dashboard is served by the backend.** Railway builds only Python, so
the dashboard's production build is committed in `assets/dashboard/` and
served at `/dashboard`, behind the same key.

## Data model

`patients` follows `docs/patient_field_spec.xlsx` field for field:

| Field | Stored as | Rule |
|---|---|---|
| `patient_id` | UUID string | Auto. The REST resource ID. |
| `member_id` | 8 digits | Auto. The ID the caller hears and later reads back to verify (a UUID can't be spoken). |
| `first_name`, `last_name` | string | 1–50 chars. Letters in any script (José, Zoë, Nguyễn), hyphens, apostrophes (curly ones are straightened), plus spaces/periods for names like "Mary Ann", "St. John". |
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

All endpoints below except `/health` need an `X-API-Key` header. Every JSON response
uses the same envelope:

```json
{ "data": { ... }, "error": null }
{ "data": null, "error": { "code": "validation_error", "message": "...", "details": [{ "field": "zip_code", "message": "..." }] } }
```

List endpoints add `"meta": { "limit": 20, "next_cursor": "..." }`. Pass
`?cursor=` to get the next page.

| Method | Path | Notes |
|---|---|---|
| GET | `/patients` | Filters: `?last_name=` (case-insensitive), `?date_of_birth=` (either format), `?phone_number=` (any format), `?member_id=`, `?possible_duplicates=true`, `?include_deleted=true` |
| GET | `/patients/{patient_id}` | 404 if unknown or soft-deleted, 400 if not a UUID |
| GET | `/patients/{patient_id}/duplicates` | Other active records with the same name, DOB and phone (see the Duplicates decision above) |
| POST | `/patients` | 201 with the created record. 409 if the same person (name + DOB + phone) already exists. |
| PUT | `/patients/{patient_id}` | Partial update: only the fields sent change. `null` clears an optional field. Required fields can't be cleared. |
| DELETE | `/patients/{patient_id}` | Soft delete: sets `deleted_at` and returns the record |
| GET | `/calls`, `/calls/{call_id}` | `?patient_id=` lists the calls that registered or verified a patient |
| GET | `/logs` | Log records, newest first (kept 90 days). Filters: `?since=`, `?until=` (ISO datetimes), `?level=` (minimum level), `?event=`, `?hide_http=true`, `?call_id=`, `?request_id=` |
| GET | `/logs/events` | Every event name logged so far, for filtering |
| GET | `/stats` | Headline counts for the dashboard: live calls, calls and new patients in the last 24h, average call duration, totals, possible duplicates, errors and warnings |
| GET | `/health` | No auth. Checks the database connection. |
| GET | `/docs`, `/redoc`, `/openapi.json` | API docs. The browser asks for a login (any username, the API key as password); `/openapi.json` also takes the header. |
| GET | `/dashboard` | The web dashboard (pre-built from `../dashboard`, committed in `assets/dashboard/`). Needs the key: the browser asks for a login (any username, the API key as password), then a session cookie covers the dashboard's API calls. |

Every route, including the Retell and dashboard ones, with its auth, is listed in
[`../docs/api-routes.md`](../docs/api-routes.md) (kept in step with the app by
`tests/test_api_routes_doc.py`).

The Retell routes aren't part of this API: `POST /retell/tools/*` (the four
tools in the Architecture diagram) and
`POST /retell/webhook` need Retell's
`X-Retell-Signature` instead of the key. `GET /retell/webhook` is an open
reachability check. For the live list with request and response schemas, open
`/docs`.

To print every route the app registers, including the ones hidden from
`/docs` (the docs pages and the dashboard), run this from `backend/`. It
doesn't connect to the database, but settings need `MONGODB_URI` set (your
`.env`, or any placeholder):

```bash
python -c "from app.main import create_app; [print(*sorted(r.methods - {'HEAD'}), r.path) for r in create_app().routes if hasattr(r, 'methods')]"
```

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
welcome ("register, or check/update an existing registration?")
 ├─ register ─> reg_collect (name spelled and spelled back, DOB, sex, phone,
 │               address; optional email, insurance, emergency contact, language)
 │               ─> full read-back ─> caller confirms
 │               ─> reg_create (create_patient)
 │                    ├─ created ─> reg_success (member ID read in groups)
 │                    ├─ invalid ─> reg_fix (re-ask that one field) ─> reg_create
 │                    └─ else (error, timeout) ─> system_error (apology, ends call)
 ├─ check/update ─> verify_collect (member ID + full name + DOB, read back)
 │                   ─> verify_check (verify_patient)
 │                        ├─ verified ─> manage_profile (read back / update, via
 │                        │              get_patient_profile, update_patient_profile)
 │                        └─ else ─> verify_failed (ends call, reveals nothing)
 ├─ forgot member ID ─> forgot_member_id (in person with photo ID, or register)
 └─ nothing needed ─> end_goodbye
```

Every conversation node can reach `end_goodbye` when the caller wants to
stop, and the three closing lines are spoken in the caller's language.

### Prompt design, and why

- **One identity and scope in the global prompt.** Sarah is a registration
  coordinator, not a clinician. That keeps the agent out of triage.
  Appointments, billing, test results and medical questions go to the front
  desk. A caller who describes a medical emergency is told to hang up and
  call 911. That's a scope rule, not an opening disclaimer, so the greeting
  stays short.
- **Security rules in the global prompt, enforced again on the server.**
  Nothing about a record is said before member ID + full name + DOB verify,
  a failure never says which detail was wrong, and a member ID is never
  looked up by name or DOB.
- **Nothing is saved until the caller confirms a full read-back.** Names
  and emails are spelled back letter by letter at collection and again in
  the summary, so a mishearing is caught before it becomes a record.
- **Out-of-order answers and corrections are handled in the prompt.** A
  correction replaces the value and only the corrected part is read back.
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
  can't be in the future."). `reg_fix` re-asks only the failing field.
- **Branching is on values the server returns**, not on the model's reading
  of them: `create_status` and `verification_result` drive equation edges.
  `tests/test_flow_contract.py` checks those values, the tool URLs and the
  argument names against the backend.
- **Languages.** The agent is configured for 12 locales (`en-US`, `en-GB`,
  `en-IN`, `es-ES`, `es-419`, `zh-CN`, `fr-FR`, `de-DE`, `hi-IN`, `ru-RU`,
  `it-IT`, `pt-PT`). On "Hablo español" the call continues in Spanish, while
  tool arguments keep their canonical formats. Names in any script are
  accepted (see Data model), so a Spanish or Hindi speaker's name registers
  as they spell it.

## Edge cases

| Scenario | What happens |
|---|---|
| Invalid DOB / 3-digit phone | The server rejects it with a speakable reason. `reg_fix` re-asks only that field, then saves again. |
| Caller corrects a field ("D-A-V-I-S, not D-A-V-I-E-S") | The prompt replaces the value and confirms just that field. The full read-back before saving catches anything missed. |
| Caller wants to start over | No dedicated node. Nothing is saved before the confirmed read-back, so the model re-collects within `reg_collect`. Once saved, changes go through verification and `manage_profile`. |
| Database write fails | The tool returns HTTP 500 and Retell takes the else-edge to `system_error`, which apologizes and ends the call. There is never silence (see `test_db_failure_returns_error_not_silence`). |
| Tool call retried by Retell | `create-patient` is idempotent per call + name + DOB. Updates are naturally idempotent. |
| Call drops mid-registration | Nothing is written until the caller confirms the read-back, so there are no half-records. The webhook still records the call, its transcript and its `disconnection_reason`. On the next call they start over. |
| Returning caller registers again | With their member ID they verify and update instead. Without it, a phone + name + DOB match is saved as a new record and never mentioned, because saying so would confirm a record to an unverified caller. Staff see the pair on the dashboard (see the Duplicates decision above). |
| Accented or non-Latin name (José, Nguyễn, अनिल) | Accepted and stored as spelled. A curly apostrophe (O’Brien) is stored as a straight one, and accents typed as separate marks are merged into their letters, so verification and duplicate checks match either way (`clean_name_text` in `core/validation.py`). |
| Household sharing one phone | A phone match alone isn't treated as a duplicate: a household member with a different name or DOB registers normally. |
| Wrong verification details | One generic failure message, then the call ends. Which detail was wrong is never revealed. Soft-deleted patients can't verify. |

## Observability

Modules log through `core/logger.py`'s `EventLogger`: one structured line
per event to stdout (Railway's log view), also batched into the `logs`
collection (90-day TTL) and readable at `GET /logs` and on the dashboard.
Every record carries its request's `request_id` (also the `X-Request-ID`
response header).

- `http_request`: one per request.
- `retell_tool`: one per tool call, with the arguments Retell sent and the
  response.
- `retell_webhook`: the full webhook body. `call_ended` carries the
  transcript and `call_analyzed` the summary; both are also stored on the
  `calls` document, linked to the patient.
- `patient_created` / `patient_updated` with the final payload, plus
  `patient_duplicate_detected`, `patient_create_replayed` and
  `patient_deleted`.

A MongoDB failure only drops log records; it never fails a request.

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
| `MONGODB_DB` | Database name (default `patient_registration`, which production uses). Set `patient_registration_dev` locally so test runs stay out of production's data and logs. |
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
  matching. Accents count: "José" doesn't verify as "Jose". There's no lockout across calls after repeated failed
  verification, and no human escalation path.
- **No scheduling.** The line handles registration only; callers who ask
  about appointments are sent to the front desk. A mock scheduling backend
  is kept on the `feature/appointment-scheduling` branch.
- **One shared API key**, not per-user auth or roles.
- **No merge action.** Staff can see possible duplicates but merge them
  outside this system.
- **Duplicate detection needs name + DOB + phone together.** A patient who
  changed their phone number won't be caught; a person merges those records
  in person.
- **Atlas Network Access** is open (0.0.0.0/0) for deploy convenience.
  Production would allowlist Railway's egress.

## Next steps

- A merge action for possible duplicates.
- A lockout or escalation to a human after N failed verifications across calls.
- Per-user dashboard auth, and PHI redaction in logs.
- Scheduling as its own line or agent, backed by a provider calendar.
- Fuzzy name matching for verification and duplicates (e.g. "Jon" vs "John").
