# AGENTS.md

Notes for any agent (human or AI) picking up this repo.

## What this is

A take-home coding challenge from CareCloud: build a voice AI agent for patient
pre-registration. The brief (`docs/CONFIDENTIAL/`, gitignored — candidate-only material)
specifies a registration flow with a patient data model and API spec, and offers
appointment scheduling as an optional bonus.

## Where we are

Design phase, no code yet. `docs/identity-carecloud-voiceagent.html` is a research memo
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
| `playground/` | Scratch/experiment space | No (gitignored) |
| `.idea/` | PyCharm project config — Python 3.14, Black formatter | No (gitignored) |

The submitted README and code will live at the repo root once the build starts.

## Stack

Python 3.14 (per `.idea/CareCloudVoiceAgent.iml`), formatted with Black. No dependencies,
build tooling, or source code committed yet.

## Next steps

Nothing implemented yet. Next: pick the voice/telephony + LLM stack, define the system
prompt around the identity above, and implement the registration flow against the data
model in `patient_field_spec.xlsx`.
