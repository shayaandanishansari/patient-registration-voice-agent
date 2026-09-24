# Design decisions

The forks in the road: where the brief left a choice open, or where following it
literally would have caused a problem. Each entry lists what was chosen, why, and what it
costs. Implementation-level decisions (layers, idempotency, cursor paging, logging) are in
[`backend/README.md`](../backend/README.md#architecture-decisions).

## What kind of phone line this is

**Choice.** A pre-registration and patient-access line. Sarah is an intake coordinator.
She isn't a hospital switchboard and she isn't nurse triage.

**Why.** The brief asks for registration and also suggests appointment scheduling as a
bonus. Each points to a different agent. Real hospitals split phone lines by call type,
and pre-registration is its own desk. Settling this first decided much of what follows:
the scope rules in the prompt, how a caller proves who they are, and what the agent
refuses to do. The research is in
[`identity-voiceagent.html`](identity-voiceagent.html).

**Cost.** Callers with anything else (appointments, billing, results, medical questions)
are sent to the front desk instead of being helped.

## Returning callers verify with member ID + full name + date of birth

**Choice.** Before the agent touches an existing record, the caller gives their member
ID, full name and date of birth, and all three must match. The member ID is 8 random
digits, handed out at registration. It is a separate ID from the `patient_id` UUID the
brief specifies for the REST API.

**Why.** Name, date of birth and phone number are all things a relative, an ex or a
stranger with an old form can know. The member ID is something only the patient was
given. A UUID can't be read back over the phone, so the agent needs a short numeric ID.

**Cost.** A caller who lost their member ID can't be verified by phone. They're offered
two options: register a new profile, which staff merge later, or visit in person with a
photo ID. The agent never looks up a member ID by name or date of birth.

## Duplicates are detected but never revealed

**What the brief asks.** If the caller's phone number matches a patient, the agent says
"It looks like we already have a record for [First Name] [Last Name]. Would you like to
update your information instead?"

**Choice.** A match needs the same phone number, name and date of birth. On the phone,
the agent saves a new record and says nothing about the match. Staff see the pair on the
dashboard (the Overview tile, the patient page, and a Patients filter). The REST API
refuses a duplicate with `409`.

**Why.** Done as written, the bonus leaks data. Anyone who reads out a phone number hears
whose record it belongs to and is offered the chance to edit it. Phone alone isn't
identity either, because households share lines. REST callers are trusted staff and
systems, so for them a clear refusal is the helpful answer.

**Cost.** Some duplicate records are created on purpose, and merging them is manual.
There's no merge button yet.

## Some things can't be done by phone

**Choice.** A verified caller can change their phone number, email and address. They
can't change their name or date of birth.

**Why.** Name and date of birth are what the caller just verified with. If the phone
line could change them, a caller who got in once could lock the patient out of their own
record. Changing them needs a person and a photo ID.

## Scheduling left out

**Choice.** No appointment booking on this line. A tested mock scheduling backend
(slots, booking, double-booking protection) exists on the `feature/appointment-scheduling`
branch and is left out of `main`.

**Why.** Scheduling is usually a separate line or agent, backed by a provider's real
calendar. Booking against mock data in the middle of a registration call would make the
agent less focused, and it wouldn't show anything true about scheduling.

**Cost.** It's the one bonus not shipped on `main`.

## Retell instead of a hand-built voice pipeline

**Options.** Twilio plus a realtime speech model (Gemini Live), bridged by our own
server, or a voice platform (Vapi, Retell, Bland).

**Choice.** Retell AI, running a node-based conversation flow on Claude Sonnet 5.

**Why.** The reviewer grades one live call, and the brief's time limit is 3 hours. A
hand-built bridge adds risk in the audio transport, which isn't what's being evaluated.
Retell gives a real number, low-latency speech and a flow editor. That leaves the time
for the prompt, the tools and the backend. Sonnet 5 is used for its instruction-following
on the security and read-back rules.

**Cost.** The conversation depends on a vendor's runtime and pricing, and the flow lives
in a Retell export (`agent.json`) rather than in code.

## A conversation flow, not one big prompt

**Choice.** The agent is a graph of nodes (collect, save, fix a field, verify, manage
the profile, end). It branches on values the server returns, not on the model's reading
of a tool result.

**Why.** Steps that matter for security can't be skipped or talked around. The caller
can't reach "manage profile" unless `verification_result` is `verified`, and that value
comes from the backend. `tests/test_flow_contract.py` checks that the flow and the
backend agree on tool URLs, argument names and those values.

**Cost.** A graph is more rigid than one free-form prompt. Natural phrasing,
out-of-order answers and corrections are handled inside each node's prompt.

## The backend decides what's true

**Choice.** The agent collects values. The backend checks and normalizes every one of
them with the same rules the REST API uses, and returns a short sentence the agent can
say. After verification, the patient is tied to Retell's `call_id` on the server. No
tool accepts a patient ID from the model.

**Why.** The brief says not to rely on the voice agent for validation. A model that is
confused or prompt-injected shouldn't be able to reach anyone else's record.

## Voice only, no keypad

**Choice.** Callers speak every answer. There's no "press 1" or typing digits on the
keypad.

**Why.** The brief asks for natural conversation, not an IVR menu, and reviewers will
test the voice.

## Names in any script, 12 languages

**Choice.** The agent runs in 12 locales. Names accept letters and accents from any
script (José, Nguyễn, अनिल, 李). Before a name is stored or compared, it's put in one
consistent form.

**Why.** The brief's rule, "alphabetic + hyphens/apostrophes", would reject many real
names if read as A–Z. A line that speaks Spanish or Hindi has to accept the names its
callers have. The multi-language bonus comes almost for free once names are handled.

**Cost.** Verification is an exact match, and accents count, so "José" doesn't verify
as "Jose".

## An emergency rule, no opening disclaimer

**Choice.** A caller who describes a medical emergency is told to hang up and call 911.
That's a scope rule in the prompt. The greeting doesn't open with a disclaimer.

**Why.** The [identity memo](identity-voiceagent.html) recommends opening with "If this is a
life-threatening emergency, hang up and dial 911," as real patient lines do, and a
production line should. This demo leaves it out on purpose: reviewers call it repeatedly
to test the flow, and a fixed disclaimer on every call makes it sound scripted.

**Cost.** A caller with an emergency hears the 911 instruction only once they describe
it, not before they say anything.

## Gaps in the brief's field table, filled in

- **`deleted_at`** was added to the patient model. The DELETE endpoint requires soft
  delete, but the field table leaves it out.
- **`member_id`** was added for phone verification (see above).
- **Name characters** were widened to any script (see above).
- **A `calls` collection** stores each call's transcript, recording and summary, linked
  to the patient it registered or verified. This covers the transcript bonus.
