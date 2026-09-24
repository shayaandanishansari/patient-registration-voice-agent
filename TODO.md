# TODO before submitting

In order.

## 1. Dashboard cleanup, `/logs` page, docs page

- [ ] General dashboard cleanup.
- [x] Persistent event log: every `EventLogger` event also goes to the `logs` collection
      (90-day TTL), readable at `GET /logs`. Best-effort; stdout logging unchanged.
- [x] `/logs` page on the dashboard: filter by time range, level, event and call.
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

- [x] Remove features the agent doesn't have (start over, 911 greeting, appointment
      booking in the call). Multi-language turned out to be real and is now documented.
- [x] Document the event log and `/logs`.
- [ ] Document the docs page and the system diagram once they exist.
- [x] Fill in the Retell phone number (the `TODO` in `README.md`).

## 4. Upload the latest agent and test it

- [ ] Import `backend/assets/retell_agent_scripts/agent.json` into Retell; number assigned,
      agent webhook URL set to `/retell/webhook`.
- [x] Decide what happens when the same person (name + DOB + phone) registers twice:
      voice registers them and never mentions it; staff see possible duplicates on the
      dashboard (see the root README).
- [ ] Test calls: register (name spelled back, optional fields), call back and verify,
      update a field, wrong DOB (security message), goodbye is spoken, the patient and
      the call show up on `/dashboard`.
- [ ] Also: register the same person twice (new member ID, nothing said, Overview tile
      goes up), and a Spanish call with an accented name (José Peña).

## Then submit

- [ ] Email: phone number, API base URL, `/dashboard` link, the API key.
