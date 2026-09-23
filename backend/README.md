# CareCloud VoiceAgent — backend

Backend for a Retell AI voice agent that pre-registers new patients and lets
verified existing patients check or update their contact details over the
phone. See `../docs/identity-carecloud-voiceagent.html` for the design
rationale (what kind of phone line this is, why verification works the way
it does) and `../AGENTS.md` for overall repo context.

## Architecture

```
caller (phone)
   |
   v
Retell AI  <-- conversation_flow.json defines the state graph, prompts,
   |            and the four custom tools below
   |
   +--> POST /retell/tools/create-patient   } tool calls during
   +--> POST /retell/tools/verify-patient    } the live call —
   +--> POST /retell/tools/get-patient        } must answer in
   +--> POST /retell/tools/update-patient    } well under 2s
   |
   +--> POST /retell/webhook   (call_started / call_ended / call_analyzed,
   |                            fired by Retell outside the tool-call path)
   v
FastAPI app (this repo)
   |
   v
MongoDB Atlas — two collections: `patients`, `calls`
   ^
   |
   +-- GET /api/patients, /api/patients/{member_id},
       /api/calls, /api/calls/{call_id}, /api/health
       (read-only, X-API-Key protected — this is what reviewers/the
       future dashboard use to see persisted data)
```

Every tool call and the webhook carry Retell's own `call_id`. Verification
state (`verified_member_id`) is stored on the `calls` document keyed by that
`call_id`, never trusted from the LLM's `args` — so a prompt-injected or
confused LLM cannot ask `get-patient`/`update-patient` for anyone else's
record (see design decision 3 below).

## Data model

Two collections only, matching `docs/patient_field_spec.xlsx` plus one
addition explained below.

- **`patients`** — `member_id` (8 random digits, easy to read aloud — this
  is separate from Mongo's own `_id`), demographics, address, optional
  insurance/emergency-contact fields from the field spec, `update_history`.
- **`calls`** — `call_id`, call metadata from the Retell webhook,
  `verified_member_id` / `verified_at` / `verification_attempts` (written
  only by the tool endpoints), `patients_created`.

`docs/patient_field_spec.xlsx` specifies `patient_id` as a UUID — fine for a
REST resource, but nobody can read a UUID back over the phone. `member_id`
is the voice-facing identifier introduced specifically so a caller can speak
it back on a later call for identity verification (Mongo's internal `_id`
still serves as the storage primary key). Insurance and emergency-contact
fields from the spec are optional and carried on the schema, but the current
`conversation_flow.json` doesn't collect them yet — see Known Limitations.

## Running locally

```bash
cd backend
python -m pip install -e ".[dev]"
cp .env.example .env   # then fill in MONGODB_URI, RETELL_API_KEY, API_READ_KEY
python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for interactive API docs.

Run tests:

```bash
python -m pytest -q
```

Tests use `mongomock-motor`, not a real database.

## Environment variables

| Variable | Purpose |
|---|---|
| `MONGODB_URI` | Atlas connection string |
| `MONGODB_DB` | Database name (default `patient_registration`) |
| `RETELL_API_KEY` | The webhook/signing key set on the Retell agent; verifies `X-Retell-Signature` |
| `PUBLIC_BASE_URL` | This deployment's public URL; used by `scripts/deploy_retell_flow.py` to rewrite tool URLs |
| `API_READ_KEY` | Required `X-API-Key` value for `/api/*` (except `/api/health`) |
| `ALLOW_UNSIGNED_REQUESTS` | `true` only for local curl testing without a real Retell signature. Logs a loud warning at startup. Never `true` in production. |
| `CORS_ORIGINS` | JSON array of allowed origins (the dashboard's dev/prod URL) |

## Deploying

1. **Atlas**: create/confirm the cluster, and under Network Access allow
   Railway's egress (0.0.0.0/0 for this project's scope — see known
   limitations on tightening this).
2. **Railway**: connect the GitHub repo, set the root directory to
   `backend/`, and set the environment variables above.
   `railway.json` supplies the start command and `/api/health` health
   check.
3. Once deployed, note the Railway URL and set `PUBLIC_BASE_URL` (locally,
   to run the next step; and on Railway itself).
4. **Push the flow to Retell**:
   ```bash
   python scripts/deploy_retell_flow.py
   ```
   This reads `retell/conversation_flow.json`, replaces every
   `https://YOUR-BACKEND.up.railway.app` placeholder with `PUBLIC_BASE_URL`,
   and creates (or, if `RETELL_CONVERSATION_FLOW_ID` is set, updates) the
   conversation flow. On first create, copy the printed flow ID into
   `RETELL_CONVERSATION_FLOW_ID` so re-runs update in place.
5. In the Retell dashboard, set this agent's **webhook URL** to
   `<PUBLIC_BASE_URL>/retell/webhook`, and assign a phone number to the
   agent.

## API examples

```bash
# A Retell tool call (normally sent by Retell, signed with X-Retell-Signature)
curl -X POST "$PUBLIC_BASE_URL/retell/tools/create-patient" \
  -H "content-type: application/json" \
  -H "x-retell-signature: $SIGNATURE" \
  -d '{
    "name": "create_patient",
    "call": {"call_id": "call-123", "from_number": "+15125550123"},
    "args": {
      "first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-03-05",
      "sex": "female", "phone": "5125550123",
      "address_line1": "123 Main St", "city": "Austin", "state": "TX", "zip_code": "78701"
    }
  }'

# Read-only REST API
curl "$PUBLIC_BASE_URL/api/patients?limit=10" -H "x-api-key: $API_READ_KEY"
curl "$PUBLIC_BASE_URL/api/patients/12345678" -H "x-api-key: $API_READ_KEY"
curl "$PUBLIC_BASE_URL/api/calls/call-123" -H "x-api-key: $API_READ_KEY"
curl "$PUBLIC_BASE_URL/api/health"   # no auth
```

## Design decisions

1. **Phone number is contact info, not identity.** A shared household line
   is normal; registration does not deduplicate on phone, and the same
   person registering twice is an accepted, recoverable outcome (merged in
   person later, not by this system).
2. **Verification requires member ID + full name + date of birth together.**
   `verify-patient` always does the same database work and returns exactly
   one of two response shapes, regardless of which part of the input was
   wrong or whether the member ID exists at all — so the flow (and a caller
   probing it) can never learn which detail failed.
3. **Post-verification access is bound to `call_id` server-side.**
   `get-patient` and `update-patient` never accept a member ID from `args`;
   they resolve the caller through `calls.verified_member_id`, keyed by
   Retell's own `call_id`. The LLM cannot be talked into fetching another
   caller's record.
4. **Verification attempts are counted per call, not rate-limited across
   calls.** Known limitation: nothing currently locks out or escalates a
   phone number after repeated failed attempts across separate calls; a
   production system would.
5. **Name and date of birth are read-only over the phone.** `update-patient`
   whitelists only contact/address fields; if the flow passes `first_name`,
   `last_name`, `date_of_birth`, `sex`, or `member_id`, they're silently
   ignored and the response says these can only be changed in person.
6. **Every tool write is idempotent**, because Retell may retry a tool call.
   `create-patient` keys off `sha256(call_id + first_name + last_name +
   date_of_birth)` and returns the same `member_id` on a retry instead of a
   duplicate record; `update-patient` is naturally idempotent (setting the
   same value twice is harmless); the webhook upserts by `call_id` and never
   touches verification state.
7. **Known limitations / next steps with more time:**
   - Fuzzy name matching for verification (currently exact, case-insensitive).
   - Human escalation path after repeated failed verification.
   - Audit export of `update_history` / verification attempts.
   - Atlas Network Access is currently open (0.0.0.0/0) for this
     take-home's deployment convenience; production would allowlist
     Railway's static egress ranges instead.
   - Insurance and emergency-contact fields exist on the `patients` schema
     (per `docs/patient_field_spec.xlsx`) but aren't yet collected by
     `conversation_flow.json` — a future flow revision would add a
     collection step and wire the corresponding `create-patient` /
     `update-patient` args through.
