# School AI Assistant

An AI chat assistant that answers parents' questions about **one childcare center at a time**,
using only that center's own information. Center admins can edit the information, see who changed
what, and review every question asked. It is a prototype, with two made-up centers as seed data.

**Live:** https://162-243-171-212.sslip.io

## What you get
- **A demo session instead of accounts.** You pick Parent or Admin and a center. The session is
  then locked to that center on the server. "Start over" on every screen resets it.
- **Grounded answers.** Claude answers only from the center's data and cites the sections it
  used. If the answer isn't there, it says so, and the server adds the center's real phone number
  and email. The model never writes those itself.
- **Answers in the asker's language** (e.g. Spanish in, Spanish out).
- **An admin editor** for the directory, hours, closures, daily schedule, fees, lunch menu and
  policies. Every change records the admin's name with before/after values, and admins can reset
  their center to the original data.
- **Q/A logs with personal info removed.** Admins see their own center's questions and answers,
  with an "unanswered" filter. Personal details are removed before anything is stored, and IPs
  are never stored.
- **Per-IP limits** on request count and token use, kept in memory only.
- Mobile-first UI, themed per center. Deployed by hand to a DigitalOcean droplet.

## How it works
| Piece | Choice | Why |
|---|---|---|
| App | FastAPI + plain HTML/JS, one process | Small, no build step; same shape as Civic Mined |
| Data | One SQLite file: typed tables for facts, markdown rows for policies | Facts get exact edit forms; prose stays prose; one store makes the change history and reset uniform |
| Center separation | `center_slug` on every row; the center comes only from the server-side session | A client can't switch centers by editing a request |
| Retrieval | None: the whole center knowledge base (~8k tokens) goes in the prompt | It fits, so nothing can be missed; cached per center (prompt caching), so repeat questions cost ~35 new input tokens |
| Answering | Claude Sonnet 5.5 with structured output `{answer, found, sources}`, effort `low` | The server checks every cited section exists and adds contacts itself |
| Log scrubbing | Regex (phones/emails/addresses/numbers), then Claude Haiku 4.5 (names, birth dates, medical details) | Cheap first pass; Haiku catches what regex can't. Staff names and the center's own contact details are kept |

The code is in `app/` (API), `static/` (UI), `seed/` (center data) and `deploy/` (Docker, Caddy, deploy script).

## Run locally
```bash
uv sync
ANTHROPIC_API_KEY=... uv run uvicorn app.main:app --reload
```
Then open http://localhost:8000. The database (`data/school.db`) is created and seeded on first
start; delete it to start fresh. Every setting is listed in `.env.example`.

## Deploy
`DROPLET_IP=<ip> ./deploy/deploy.sh` from a clean checkout. See [docs/DEPLOY.md](docs/DEPLOY.md).

## Docs
[Architecture](docs/ARCHITECTURE.md) · [Contracts](docs/CONTRACTS.md) ·
[Knowledge maintenance](docs/KNOWLEDGE_MAINTENANCE.md) ·
[Process and phases](docs/PROCESS.md) · feature docs in [docs/features/](docs/features/)
