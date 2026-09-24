# Hospital VoiceAgent - patient registration by phone

Call a real U.S. number and talk to **Sarah**, a voice AI intake coordinator.
She registers you as a new patient through natural conversation, reads
everything back for confirmation, saves it, and gives you a member ID. Call
back later and she can verify you and update your details.
Every record is also available through a REST API and a small web dashboard.

## Live demo

| |                                                                                                                             |
|---|-----------------------------------------------------------------------------------------------------------------------------|
| **Phone number** | `+1-412-223-8469`                                                                                                           |
| **API base URL** | https://patient-registration-voice-agent-production-f401.up.railway.app                                                     |
| **API docs** | [`/docs`](https://patient-registration-voice-agent-production-f401.up.railway.app/docs) (OpenAPI): the browser asks for a login; any username, the API key as password |
| **Dashboard** | [`/dashboard`](https://patient-registration-voice-agent-production-f401.up.railway.app/dashboard): the browser asks for a login; any username, the API key as password |
| **API key** | Sent separately. Pass it as the `X-API-Key` header. Only `/health` needs none.                |

Things to try on a call:
- **Register:** answer in any order, correct yourself ("actually it's
  D-A-V-I-S"), or give a future birth date or a 3-digit phone number and hear
  just that field re-asked. Sarah spells your name back and reads a full
  summary before saving, then gives you a member ID.
- **Optional details:** after the required fields, Sarah offers insurance,
  emergency contact and preferred language.
- **Check or update:** call back with your member ID, name and DOB. Sarah
  reads your record back and changes your phone, email or address. Name and
  DOB can't be changed by phone.
- **Wrong details:** a verification that doesn't match ends the call without
  saying which detail was wrong.
- **Forgot your member ID:** Sarah won't look it up by name or DOB. She
  suggests visiting in person with a photo ID, or registering a new profile.

Then look at the data:

```bash
BASE=https://patient-registration-voice-agent-production-f401.up.railway.app
curl "$BASE/patients?last_name=doe" -H "x-api-key: $KEY"
curl "$BASE/calls?limit=5" -H "x-api-key: $KEY"   # includes transcripts
curl "$BASE/logs?since=2026-09-24T00:00:00Z&hide_http=true" -H "x-api-key: $KEY"
```

## Architecture

```
Phone call ⇄ Retell AI (telephony + STT/TTS + Claude Sonnet 5 conversation flow)
                 │  signed tool calls & webhooks
                 ▼
           FastAPI backend ── routers / services / models / core
                 │                     ▲
                 ▼                     │ REST API (API key)
           MongoDB Atlas ◀─────────────┤
                                       └── React dashboard
```

| Layer | Choice | Why |
|---|---|---|
| Telephony + voice | **Retell AI** | A real number, low-latency speech and a node-based conversation flow in one platform. The time goes into the prompt and backend, not audio plumbing. |
| LLM | **Claude Sonnet 5** (via Retell) | Strong instruction-following and tool calling at conversational latency. |
| Backend | **Python / FastAPI** | Async (tool calls must answer fast), Pydantic validation, OpenAPI for free. |
| Database | **MongoDB Atlas** (Motor) | Managed and persistent. A document per patient, plus a `$jsonSchema` validator enforcing the field spec. |
| Hosting | **Railway** | GitHub deploys with a health check. |
| Dashboard | **Vite + React + TanStack Query + Tailwind** | Small internal SPA. API types are generated from the backend's OpenAPI schema. |

## Repository layout

| Path | |
|---|---|
| [`backend/`](backend/README.md) | FastAPI service, tests, and the Retell agent export (`assets/retell_agent_scripts/agent.json`, which contains the full system prompt and conversation flow) |
| [`dashboard/`](dashboard/README.md) | Web UI over the API. Its production build is committed to `backend/assets/dashboard/` and served at `/dashboard` |
| [`docs/`](docs/README.md) | Field spec, the design memo on what kind of phone line this is, and the security review ([`docs/security.md`](docs/security.md)) |
| `playground/` | Early experiments (DB connection, Retell API) kept as a record of the testing approach |

**[`backend/README.md`](backend/README.md) is the detailed write-up.** It
covers the data model, API reference and status codes, the conversation
flow and prompt design, the edge cases (invalid input, dropped calls,
database failures), observability, environment variables,
deployment, and known limitations.

## Running locally

```bash
# backend (Python 3.11+)
cd backend
python -m pip install -e ".[dev]"
cp .env.example .env        # MONGODB_URI, API_KEY, RETELL_API_KEY
python -m uvicorn app.main:app --reload
python -m pytest -q         # no database needed (mongomock)

# dashboard (Node 20+)
cd dashboard
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Environment variables

Backend: `MONGODB_URI`, `MONGODB_DB`, `API_KEY`, `RETELL_API_KEY`,
`ALLOW_UNSIGNED_REQUESTS` (local only), `CORS_ORIGINS`, `PUBLIC_BASE_URL`,
`LOG_LEVEL`. See `backend/.env.example`. Dashboard: `VITE_API_BASE_URL`
(optional). No secrets are in the source.

## Security

Every route that touches data needs the API key or a Retell signature; only
`/health` and a webhook reachability check are open. Retell's tool calls and webhooks are HMAC-signed with the
Retell API key and rejected if older than 5 minutes. The dashboard and
`/docs` ask for the key through the browser's login prompt, then use an
HttpOnly session cookie. A test sweeps every route to enforce this. Details
in [`docs/security.md`](docs/security.md).

## Bonus challenges

| Bonus | Status | How it's handled |
|---|---|---|
| **Duplicate detection** | Done, with stronger identity checks | Returning callers are recognized and offered an update instead of a new record: Sarah verifies member ID + full name + DOB, then reads the record back and updates it. Caller ID alone isn't used as identity because households share phone lines ([`docs/identity-voiceagent.html`](docs/identity-voiceagent.html)). Creating a patient also checks for a duplicate on phone + name + DOB (the REST API returns `409`). |
| **Appointment scheduling** | Deliberately out of scope | Scheduling is usually a separate line or agent, so Sarah stays a registration and patient-information coordinator. Callers who ask about appointments are sent to the front desk. A tested mock scheduling backend (slots, booking, double-booking protection) is on the [`feature/appointment-scheduling`](https://github.com/shayaandanishansari/patient-registration-voice-agent/tree/feature/appointment-scheduling) branch, left out of `main` to keep the service focused. |
| **Multi-language** | Done, beyond Spanish | The agent runs in 12 locales: English (US, GB, IN), Spanish (ES, Latin America), Mandarin, French, German, Hindi, Russian, Italian and Portuguese. Say "Hablo español" and Sarah continues in Spanish. The fixed closing lines are translated into the caller's language, and preferred language is stored on the record. |
| **Call recording / transcript** | Done | Retell's webhook stores the transcript, recording URL and call analysis (summary) on a `calls` document linked to the patient it registered or verified. Visible in `GET /calls` and the dashboard. |
| **Dashboard** | Done | [`/dashboard`](https://patient-registration-voice-agent-production-f401.up.railway.app/dashboard): overview stats, patients, calls with transcripts, and logs. |
| **Automated tests** | Done | 144 pytest tests over the API, voice tools, webhook, validation and security (no database needed). A contract test checks the Retell flow's tool URLs and arguments against the backend. |

## Known limitations and trade-offs

- The duplicate check on create isn't a branch in the call flow yet. A
  registered patient who starts a *new* registration with the same phone,
  name and DOB hears Sarah say there was trouble saving, instead of being
  offered to update.
- The call flow was designed and tested mostly in English. Other languages
  rely on the model's translation of the same prompts.
- Verification is exact match (case-insensitive), with no lockout across
  calls after repeated failures.
- A single shared API key, not per-user auth.
- The collected payload and transcripts are logged to stdout because the
  brief asks for it, and every log event is also kept in MongoDB's `logs`
  collection for 90 days (`app/core/logger.py`). With real PHI they would be
  redacted.
- Duplicate detection needs name + DOB + phone to all match. It won't catch
  someone who changed their phone number.

## Next steps

- Branch the call flow on a duplicate at create (offer to verify and update).
- Lockout and human escalation after repeated failed verifications.
- Per-user dashboard auth, and PHI redaction in logs.
- Scheduling as its own line or agent, backed by a provider calendar.
- Fuzzy matching for names in verification and duplicate detection.
- In production, ship stdout as JSON to a log platform (Datadog, Grafana Loki)
  instead of storing logs in the application database, and replace
  `EventLogger` with structlog.
