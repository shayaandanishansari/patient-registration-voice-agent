# docs

Design notes and reference material for the Hospital VoiceAgent take-home. Everything here
is tracked in git except `CONFIDENTIAL/` (the assessment brief itself). The reviewer-facing
overview is the root `README.md`; the backend write-up is `backend/README.md`.

| File | What it is | Tracked? |
|---|---|---|
| `identity-voiceagent.html` | Design research memo deciding what kind of phone line this agent is (pre-registration / patient access, not a general switchboard or nurse triage) and why. It drives the system prompt's scope, the identity-verification approach, the emergency rule, and why duplicates are never revealed to an unverified caller. | Yes |
| `patient_field_spec.xlsx` | The patient data model field by field (type, validation rule, required), plus a Calls sheet. The backend's models and `$jsonSchema` validator follow it. | Yes |
| `security.md` | How we checked that only verified callers reach the backend and the Retell agent: the auth on each route, what Retell's docs say about signed requests and web calls, the empty-key hole we fixed, and the pre-launch checklist. | Yes |
| `CONFIDENTIAL/Voice AI Agent Coding Challenge.pdf` | The original take-home brief: requirements, data model, API spec, scoring rubric. Marked confidential / for candidate use only — kept out of git. | No (gitignored) |
