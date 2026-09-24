# docs

Working notes for the Hospital VoiceAgent take-home. Design research here is tracked in git;
only `CONFIDENTIAL/` (the assessment brief itself) is gitignored. The submitted README and code
live at the repo root once the build starts.

| File | What it is | Tracked? |
|---|---|---|
| `identity-voiceagent.html` | Design research memo deciding what kind of phone line this agent is (pre-registration / patient access, not a general switchboard or nurse triage) and why — drives the system prompt's scope, identity-verification approach, and emergency disclaimer. | Yes |
| `security.md` | How we checked that only verified callers reach the backend and the Retell agent: the auth on each route, what Retell's docs say about signed requests and web calls, the empty-key hole we fixed, and the pre-launch checklist. | Yes |
| `CONFIDENTIAL/Voice AI Agent Coding Challenge.pdf` | The original take-home brief: requirements, data model, API spec, scoring rubric. Marked confidential / for candidate use only — kept out of git. | No (gitignored) |
