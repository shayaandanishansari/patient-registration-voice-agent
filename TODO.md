# TODO before submitting

In order.

## 1. Dashboard cleanup, `/logs` page, docs page

- [ ] General dashboard cleanup.
- [ ] **Persistent event log**: a new `events` collection in MongoDB, written at the
      points that already log to stdout. Only new events from here on; no backfill of
      earlier testing.
  - Tool calls: tool, call ID, result, patient ID if known, duration.
  - Rejected input: field and the reason given.
  - Verification attempts: result only (never which detail was wrong).
  - Patient created / updated / deleted: source (voice or API), call ID, fields changed,
    old → new values.
  - Rejected requests: path, reason (missing/bad signature or API key), caller IP.
  - Server errors: path, error type, request ID.
  - Call started / ended (webhook), linked by call ID.
  - Rules: best-effort (a failed log write never breaks a request), doesn't slow tool
    responses, `/events` endpoint behind the API key, stdout logging stays as it is.
- [ ] `/logs` page on the dashboard: filterable timeline (by call, patient, event type,
      errors only), with a per-call step-by-step view.
- [ ] Docs page on the dashboard with the documents, including the new system diagram.
      The dashboard page is public: only include docs fine for anyone to read, never
      anything from `docs/CONFIDENTIAL/`.
- [ ] Rebuild the served copy (`npm run build:backend` in `dashboard/`) and commit it.

## 2. Test the security of it all

- [ ] Railway: `ALLOW_UNSIGNED_REQUESTS=false` is actually deployed (it was still on at
      last check), and `RETELL_API_KEY` matches Retell.
- [ ] Re-check: unsigned `/retell/tools/*` and `/retell/webhook` requests → 401;
      `/patients`, `/calls`, `/logs` without the key → 401.
- [ ] Optionally delete the `probe` call record left by the earlier unsigned test.

## 3. Make AGENTS.md and the READMEs accurate

- [ ] Remove features the agent doesn't have (Spanish switching, start over, 911
      greeting, appointment booking in the call).
- [ ] Document the event log, `/logs`, the docs page and the system diagram.
- [ ] Fill in the Retell phone number (the `TODO` in `README.md`).

## 4. Upload the latest agent and test it

- [ ] Import `backend/assets/retell_agent_scripts/agent.json` into Retell; number assigned,
      agent webhook URL set to `/retell/webhook`.
- [ ] Decide what happens when the same person (name + DOB + phone) registers twice: it
      currently ends the call on "trouble saving". Add a flow branch, or turn the check
      off for calls.
- [ ] Test calls: register (name spelled back, optional fields), call back and verify,
      update a field, wrong DOB (security message), goodbye is spoken, the patient and
      the call show up on `/dashboard`.

## Then submit

- [ ] Email: phone number, API base URL, `/dashboard` link, the API key.
