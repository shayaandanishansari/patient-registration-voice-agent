# Costs

What a call costs to run, where the money goes, and where to see it live. The figures come
from Retell's pricing for this agent, and they match the `call_cost` Retell reports on
real calls to this line.

## Per minute of a call

| Part | What it does | Per minute |
|---|---|---|
| LLM: Claude Sonnet 5 | Runs the conversation | $0.064 |
| Voice engine (Retell) | Speech recognition, turn-taking, orchestration | $0.055 |
| Text to speech (Retell platform voice) | Sarah's voice | $0.015 |
| **Retell agent, total** | What Retell's dashboard shows for this agent | **$0.134** |
| Telephony (Twilio, through Retell) | The phone line itself. Phone calls only; web test calls skip it. | $0.015 |
| **A phone call, total** | | **$0.149** |

On top of that, each call pays about **$0.02 once** for post-call analysis (`gpt-5.6-terra`
writes the summary shown on the dashboard), whatever the call's length.

The LLM is the biggest share of a phone minute (43%), then the voice engine (37%). Text to
speech and telephony are 10% each.

## Fixed costs

| Item | Cost |
|---|---|
| Phone number (a Twilio number bought through Retell) | $2 / month |
| MongoDB Atlas | Free (M0 tier) |
| Railway (the backend and dashboard) | Usage-based. One small always-on service. |

## What that comes to

| Example | Cost |
|---|---|
| A 33-second phone call (measured) | $0.10: voice engine 3.0¢, LLM 3.5¢, TTS 0.8¢, telephony 0.8¢, analysis 2.1¢ |
| A typical registration, about 3.5 minutes | about $0.54 |
| 1,000 registrations a month | about $540, plus $2 for the number |

A registration's length is mostly the read-backs. Names and emails are spelled letter by
letter, and the full summary is read before saving. Those read-backs are what keep
mishearings out of the records, so they stay.

## Seeing it live

Retell sends each call's cost (in cents, with a breakdown per product) in its webhook.
The backend stores it on the call as `call_cost`. The dashboard shows:

- **Overview:** a "Spend" tile, the last 24 hours and all time (`GET /stats`).
- **Each call:** the total and the breakdown on the call's page (`GET /calls/{call_id}`).

A call's cost arrives with Retell's end-of-call webhooks, so a call in progress counts as
$0 until then.

## If it had to cost less

- **A smaller LLM** would cut the biggest line. The trade-off is instruction-following on
  the security rules (never reveal a record before verification, never say which detail
  was wrong) and on the spelling read-backs. A cheaper model would need testing on
  exactly those before a switch.
- **Turning off post-call analysis** saves about 2¢ a call, but staff lose the call summary.
- **Shorter calls** mean fewer read-backs, which trades money for accuracy. I wouldn't cut
  them on a registration line.
