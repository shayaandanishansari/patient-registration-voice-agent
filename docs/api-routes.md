# API routes

Every route the backend serves, grouped by who calls it. Base URL:
`https://patient-registration-voice-agent-production-f401.up.railway.app`.
`backend/tests/test_api_routes_doc.py` fails if this list and the app's routes
disagree, so it stays current.

## How access works

| Auth | Who uses it | How |
|---|---|---|
| **API key** | Staff tools, the dashboard, scripts | `X-API-Key: <key>` header, or the session cookie the dashboard gets at sign-in |
| **Browser login** | People opening a page (dashboard, API docs) | The browser's login prompt: any username, the API key as password. Sets the session cookie |
| **Retell signature** | Retell's servers during and after a call | `X-Retell-Signature`, checked against `RETELL_API_KEY` |
| **Public** | Railway, Retell's connectivity test | Nothing. These routes return no data |

A request without valid auth gets `401`. `backend/tests/test_security.py` checks that
every route except the two public ones refuses anonymous requests.

Every JSON response uses the same envelope: `{"data": ..., "error": null}` on success,
`{"data": null, "error": {...}}` on failure. List endpoints add
`"meta": {"limit", "next_cursor"}`. To get the next page, pass `next_cursor` back as
`?cursor=`. `limit` defaults to 20 and goes up to 100.

## Patients (REST API)

The brief's CRUD API. The same validators check a REST request and a voice tool call.

| Method | Path | Auth | What it does |
|---|---|---|---|
| `GET` | `/patients` | API key | Lists active patients, newest first. Filters: `last_name` (exact, any case), `date_of_birth` (MM/DD/YYYY or YYYY-MM-DD), `phone_number` (any U.S. format), `member_id`, `possible_duplicates=true`, `include_deleted=true`. |
| `GET` | `/patients/{patient_id}` | API key | One patient by UUID. `400` if the ID isn't a UUID, `404` if there's no such patient. |
| `GET` | `/patients/{patient_id}/duplicates` | API key | Other active records with the same name, date of birth and phone number, oldest first. Staff use this to merge records that voice registration saved as new ones. |
| `POST` | `/patients` | API key | Creates a patient and returns it with `patient_id` and `member_id` (`201`). `422` names each invalid field. `409` if the same name, date of birth and phone number already exist. |
| `PUT` | `/patients/{patient_id}` | API key | Partial update: only the fields you send change. Each change is recorded in `update_history`. `400` if the body is empty. |
| `DELETE` | `/patients/{patient_id}` | API key | Soft delete: sets `deleted_at` and keeps the record. Lookups skip it unless `include_deleted=true`. |

## Calls, logs and stats (dashboard data)

Read-only views of what the voice agent did.

| Method | Path | Auth | What it does |
|---|---|---|---|
| `GET` | `/calls` | API key | Calls, newest first: status, duration, transcript, summary, recording link. `patient_id` narrows the list to calls that registered or verified that patient. |
| `GET` | `/calls/{call_id}` | API key | One call by Retell's `call_id`, including the patients it created and whether verification passed. |
| `GET` | `/logs` | API key | The event log, newest first, kept for 90 days. Filters: `since`, `until`, `level` (minimum), `event`, `hide_http`, `call_id`, `request_id`. |
| `GET` | `/logs/events` | API key | Every event name that has been logged, for the event filter. |
| `GET` | `/stats` | API key | The Overview page's counts: live calls, calls and new patients in the last 24 hours, average call length, possible duplicates, errors and warnings. |

## Voice agent tools (called by Retell mid-call)

The conversation flow calls these four while the caller is on the line. Each
request carries Retell's `call_id`. Once a caller is verified, the backend ties that
verification to the `call_id`. The model never passes a patient ID, so it can't
read or change the wrong record.

| Method | Path | Auth | What it does |
|---|---|---|---|
| `POST` | `/retell/tools/create-patient` | Retell signature | Validates and saves a new registration. Returns the new member ID, or which field to ask again for. |
| `POST` | `/retell/tools/verify-patient` | Retell signature | Checks member ID, full name and date of birth together. Returns only `verified` or `not_verified`, never the reason. |
| `POST` | `/retell/tools/get-patient` | Retell signature | Reads back the record of the patient verified on this call. |
| `POST` | `/retell/tools/update-patient` | Retell signature | Changes fields on the patient verified on this call and records each change. |

## Retell webhook (called by Retell around each call)

| Method | Path | Auth | What it does |
|---|---|---|---|
| `POST` | `/retell/webhook` | Retell signature | `call_started`, `call_ended` and `call_analyzed` events. Saves the call's timing, transcript, recording and summary, keyed on `call_id`. A repeat delivery updates the same record. |
| `GET` | `/retell/webhook` | Public | Answers the connectivity check that Retell's dashboard sends before any signed request. |

## Pages and operations

| Method | Path | Auth | What it does |
|---|---|---|---|
| `GET` | `/health` | Public | Liveness and database check. Railway's health check uses it. `503` if MongoDB is unreachable. |
| `GET` | `/dashboard` | Browser login | Redirects to `/dashboard/`. |
| `GET` | `/dashboard/{path}` | Browser login | The staff dashboard. Any path that isn't a file returns the app, and React Router picks the page. |
| `GET` | `/docs` | Browser login | Swagger UI for the REST API. |
| `GET` | `/redoc` | Browser login | The same schema in ReDoc. |
| `GET` | `/openapi.json` | Browser login | The OpenAPI schema. The dashboard's TypeScript types are generated from it. |
