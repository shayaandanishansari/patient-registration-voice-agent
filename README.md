# Hospital VoiceAgent - patient registration by phone

Call a real U.S. number and talk to **Sarah**, a voice AI intake coordinator.
She registers you as a new patient through natural conversation, reads
everything back for confirmation, saves it, and offers to book a first
appointment. Call back later and she can verify you and update your details.
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
  D-A-V-I-S"), give a future birth date or a 3-digit phone number and hear
  just that field re-asked, or say "start over" at any point.
- **Optional details:** after the required fields, Sarah offers insurance,
  emergency contact and preferred language.
- **Returning caller:** call again and give the same name, DOB and phone.
  She recognizes the record and offers to update it instead.
- **Check or update:** give your member ID, name and DOB. Sarah reads your
  record back and changes contact/address/insurance details.
- **Book an appointment** after registering (mock calendar).
- **Spanish:** say "Hablo español".

Then look at the data:

```bash
BASE=https://patient-registration-voice-agent-production-f401.up.railway.app
curl "$BASE/patients?last_name=doe" -H "x-api-key: $KEY"
curl "$BASE/calls?limit=5" -H "x-api-key: $KEY"   # includes transcripts
```

## Architecture

```
Phone call ⇄ Retell AI (telephony + STT/TTS + GPT-4.1 conversation flow)
                 │  signed tool calls & webhooks
                 ▼
           FastAPI backend ── routers / services / models / core
                 │                     ▲
                 ▼                     │ REST API (X-API-Key)
           MongoDB Atlas ◀─────────────┤
                                       └── React dashboard
```

| Layer | Choice | Why |
|---|---|---|
| Telephony + voice | **Retell AI** | A real number, low-latency speech and a node-based conversation flow in one platform. The time goes into the prompt and backend, not audio plumbing. |
| LLM | **GPT-4.1** (via Retell) | Strong instruction-following and tool calling at conversational latency. |
| Backend | **Python / FastAPI** | Async (tool calls must answer fast), Pydantic validation, OpenAPI for free. |
| Database | **MongoDB Atlas** (Motor) | Managed and persistent. A document per patient, plus a `$jsonSchema` validator enforcing the field spec. |
| Hosting | **Railway** | GitHub deploys with a health check. |
| Dashboard | **Vite + React + TanStack Query + Tailwind** | Small internal SPA. API types are generated from the backend's OpenAPI schema. |

## Repository layout

| Path | |
|---|---|
| [`backend/`](backend/README.md) | FastAPI service, tests, and the Retell agent export (`assets/retell_agent_scripts/agent.json`, which contains the full system prompt and conversation flow) |
| [`dashboard/`](dashboard/README.md) | Web UI over the API. Its production build is committed to `backend/assets/dashboard/` and served at `/dashboard` |
| [`docs/`](docs/README.md) | Field spec and the design memo on what kind of phone line this is |
| `playground/` | Early experiments (DB connection, Retell API) kept as a record of the testing approach |

**[`backend/README.md`](backend/README.md) is the detailed write-up.** It
covers the data model, API reference and status codes, the conversation
flow and prompt design, the edge cases (invalid input, dropped calls,
database failures, start-over), observability, environment variables,
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

## Known limitations and trade-offs

- Verification is exact match (case-insensitive), with no lockout across
  calls after repeated failures.
- Appointment slots are mock data (weekdays, two providers, two weeks), with
  no reschedule or cancel.
- A single shared API key, not per-user auth.
- The collected payload and transcripts are logged to stdout because the
  brief asks for it. With real PHI they would be redacted.
- Duplicate detection needs name + DOB + phone to all match. It won't catch
  someone who changed their phone number.

## Next steps

- Lockout and human escalation after repeated failed verifications.
- Per-user dashboard auth, and PHI redaction in logs.
- A real scheduling integration, with reschedule and cancel.
- Fuzzy matching for names in verification and duplicate detection.
