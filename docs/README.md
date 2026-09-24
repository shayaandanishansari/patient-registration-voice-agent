# docs

Design notes and reference material for the Hospital VoiceAgent take-home. Everything here
is tracked in git except `CONFIDENTIAL/` (the assessment brief itself). The reviewer-facing
overview is the root `README.md`; the backend write-up is `backend/README.md`.

The dashboard's Docs page (`/dashboard/docs`) shows these as cards, along with a readable
view of the Retell agent's prompt and flow. It bundles the files at build time; the list
is in `dashboard/src/features/docs/catalog.ts`. After editing a doc, rebuild the served
dashboard (`npm run build:backend` in `dashboard/`). A `docs/approach.md` shows up there
as soon as it exists.

| File | What it is | Tracked? |
|---|---|---|
| `design-decisions.md` | The judgment calls: where the brief left a choice open or would have caused a problem (duplicates, verification, scheduling, Retell), what was chosen and what it costs. | Yes |
| `api-routes.md` | Every backend route grouped by caller, with its auth. `backend/tests/test_api_routes_doc.py` keeps it in step with the app. | Yes |
| `System Architecture.svg` | The system diagram: caller, Retell, backend, MongoDB, dashboard, and the routes and auth between them. `System Architecture.excalidraw` is its editable source. | Yes |
| `identity-voiceagent.html` | Design research memo deciding what kind of phone line this agent is (pre-registration / patient access, not a general switchboard or nurse triage) and why. It drives the system prompt's scope, the identity-verification approach, the emergency rule, and why duplicates are never revealed to an unverified caller. | Yes |
| `patient_field_spec.xlsx` | The patient data model field by field (type, validation rule, required), plus a Calls sheet. The backend's models and `$jsonSchema` validator follow it. | Yes |
| `security.md` | How we checked that only verified callers reach the backend and the Retell agent: the auth on each route, what Retell's docs say about signed requests and web calls, the empty-key hole we fixed, and the pre-launch checklist. | Yes |
| `archive/` | Superseded drafts (early agent exports, prompts, session notes), kept locally for reference. | No (gitignored) |
| `CONFIDENTIAL/Voice AI Agent Coding Challenge.pdf` | The original take-home brief: requirements, data model, API spec, scoring rubric. Marked confidential / for candidate use only — kept out of git. | No (gitignored) |
