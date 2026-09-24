# Security: who can reach what

This note records how we checked that only verified callers can reach the backend and the
Retell agent, and what we changed as a result. It covers both halves of the system: the
FastAPI backend we run, and the Retell agent that calls into it.

## The question

Can anyone who isn't meant to reach patient data get to it, whether through the REST API,
the dashboard, the Retell tool endpoints, or the phone line itself?

## Backend

### What we reviewed

- `app/core/security.py`, which holds the two ways in: an `X-API-Key` check for the REST
  API, and a Retell signature check (`X-Retell-Signature`) for `/retell/*`.
- How each router attaches those checks (router-level `dependencies=[...]`).
- The unauthenticated routes, to confirm none of them returns patient data.
- The installed Retell SDK's verify code (`retell/lib/webhook_auth.py`), to see exactly
  what a valid signature is: `v=<timestamp>,d=<HMAC-SHA256 of body + timestamp>`,
  rejected when the timestamp is more than 5 minutes off.

### What we found

| Route | Protection |
|---|---|
| `/patients`, `/calls`, `/appointments` | `X-API-Key` (or the dashboard's session cookie), compared in constant time. No key configured means every request is refused. |
| `/retell/tools/*`, `POST /retell/webhook` | Valid `X-Retell-Signature` over the raw body, max 5 minutes old (stops replays). |
| `/health` | Public. Returns only `ok` / database status. |
| `/dashboard` | The same API key, via the browser's login prompt; see below. |
| `GET /retell/webhook` | Public reachability probe. Always returns `ok`. |
| `/docs`, `/redoc`, `/openapi.json` | The same API key. A browser can't attach `X-API-Key` when opening a page, so the key is also accepted as the password of the browser's login prompt (HTTP Basic, any username). `npm run gen:api` sends the header via `dashboard/redocly.yaml`. |

One real hole: if `RETELL_API_KEY` was unset, the signature check used an **empty
secret**. Anyone can compute an HMAC with an empty key, so they could have forged Retell
tool calls and created or read patient records.

### What we changed

- **Fail closed on a missing Retell key.** With `RETELL_API_KEY` unset, every `/retell/*`
  request is now rejected (`app/core/security.py`).
- **No unsigned mode when deployed.** With `ALLOW_UNSIGNED_REQUESTS=true`, the app refuses
  to start on Railway (`RAILWAY_ENVIRONMENT_NAME` set) or when `ENVIRONMENT=production`.
  It used to only log a warning (`app/main.py`, `app/core/config.py`).
- **Startup warnings** when `RETELL_API_KEY` or `API_KEY` is unset.
- **API docs behind the key.** `/docs`, `/redoc` and `/openapi.json` were public; they now
  need the API key (`app/routers/docs.py`). The brief doesn't ask for public docs, and it
  expects credentials to be sent with the submission.
- **The dashboard page behind the key.** It used to be public (see Dashboard below).
- **A route sweep test** (`tests/test_security.py`). It calls every registered route
  without credentials and fails unless each returns `401`. Public routes are listed
  explicitly, so a new endpoint added without auth breaks the tests. It also covers a
  wrong API key, the empty-secret signature, and unsigned mode on Railway.

### Dashboard

The dashboard used to load for anyone, showing its own sign-in screen; only the data
behind it needed the key. Now the page itself needs the key too. Its files are static,
so the backend has to check before serving them, and the browser's built-in login
prompt (HTTP Basic, any username, the API key as password) is the only way to ask.

To avoid typing the key twice, a successful login sets an `api_session` cookie, and the
dashboard's API calls carry that instead of `X-API-Key`. The cookie:

- holds an HMAC derived from the key, never the key itself, so changing `API_KEY` signs
  every browser out;
- is `HttpOnly` (page scripts can't read it), `Secure`, and `SameSite=Strict` (other sites
  can't make a browser send it);
- lasts until the browser closes.

The key is not in the built bundle (we searched `backend/assets/dashboard/` for it):
`npm run build:backend` blanks `VITE_API_KEY`. The key is the only barrier, so it should
be long and random.

## Retell

### What we looked up

We checked Retell's own documentation to confirm how requests from Retell can be trusted
and how the agent can be reached:

- **Tool calls are signed, not just webhooks.** Retell's custom-function docs say each
  request carries `X-Retell-Signature`, "an encrypted request body using your secret key",
  verified against the raw body. That matches our check.
  ([custom function](https://docs.retellai.com/build/conversation-flow/custom-function))
- **Which key signs.** "Only the API key that has a webhook badge next to it can be used to
  verify the webhook." `RETELL_API_KEY` on Railway must be that key, or every tool call
  fails with `401`. ([secure webhook](https://docs.retellai.com/features/secure-webhook))
- **Replay protection.** The signature includes a timestamp; Retell recommends rejecting
  anything older than 5 minutes, which the SDK's verify already does.
  ([Hookdeck guide](https://hookdeck.com/webhooks/platforms/guide-to-retell-webhooks-features-and-best-practices))
- **Source IP.** Retell publishes the IP its requests come from (`100.20.5.228`). We chose
  not to allowlist it: the signature already blocks forgeries, and a changed IP would
  break live calls. ([secure webhook](https://docs.retellai.com/features/secure-webhook))

### Ways to reach the agent

| Route | Who can use it |
|---|---|
| Phone number | Anyone with the number (it's in the README, by design). |
| Web calls from a website | Needs a Retell **public key**, which can be locked to a domain and require reCAPTCHA. We have not created one, so this route is closed. ([web call](https://docs.retellai.com/deploy/web-call)) |
| Retell dashboard "Test", outbound calls | Needs our Retell login or private API key. |
| Calling `/retell/tools/*` directly, pretending to be Retell | Refused with `401`: it can't be signed without our key. |

### Why an open phone line is acceptable

A caller who dials in can only do two things before verifying:

- **Register a new patient.** That's the purpose of the line. Spam registrations are
  possible, as on any registration line.
- **Nothing else.** No record is looked up, confirmed or read out until member ID, full
  name and date of birth all match. The agent never says which detail was wrong or whether
  a member ID exists. After verification, access is bound server-side to that call's
  `call_id`, so one call can't reach another patient's record. See
  `identity-voiceagent.html` for why verification works this way.

## Checklist before going live

- `RETELL_API_KEY` on Railway is the key with the webhook badge in Retell.
- `API_KEY` is set to a long random value, shared only with reviewers.
- `ALLOW_UNSIGNED_REQUESTS=false` (the app now refuses to start otherwise).
- No Retell public key is created unless web calls are wanted; if one is, lock it to the
  site's domain and turn on reCAPTCHA.
