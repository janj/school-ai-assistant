# School AI Assistant

An AI chat assistant that answers parents' questions about **one childcare center at a time**,
using only that center's own information. Admins keep that information accurate. A prototype
with two made-up centers, Juniper Hill and Little Comets.

**Live:** https://162-243-171-212.sslip.io (demo: there are no accounts; pick a role and a center)

## Features
**For parents**
- **Grounded answers** from the center's data only, with the sections used shown as source chips.
  If the answer isn't there, it says so, and the server attaches the center's real phone and
  email. Contact details never come from the model.
- **Follow-ups keep context** ("and on early release days?"). Up to 8 turns per conversation, with
  history in memory only. "New conversation" starts a fresh thread.
- **Answers in the language you ask in**, e.g. Spanish.
- **Voice:** tap the mic to ask, and turn on read-aloud for answers. It uses the browser's own
  speech features and is hidden where unsupported.
- **Per-center look:** colors, font, a light background pattern and a favicon. Mobile-first.

**For admins** (tabs: Data · History · Logs · Data issues)
- **Data editor** for center info, directory, hours, closures, daily schedule, fees, lunch menu,
  facts, policies and FAQs, plus **reset to original data**.
- **One home per fact:** policies and FAQs use placeholders such as `{{fee:registration}}`,
  inserted with a picker and checked in a preview. Editing a fee updates every policy that uses it.
  Keys can't be changed and rows in use can't be deleted, so placeholders don't break.
- **History:** every change with the admin's name and before/after values.
- **Logs:** every question and answer, with personal information removed before storage. An
  **"Answer this"** button turns an unanswered question into an FAQ entry the assistant uses
  straight away.
- **Data issues:** a maintenance agent checks for typed-in duplicates, broken placeholders, gaps
  and contradictions between sections (rule-based checks plus an AI review). It fixes only provably
  safe cases itself, recorded in History. Everything else waits for an admin.

**Safety**
- The session is locked to one center on the server, so a request can't reach another center's data.
- Per-IP request and token limits (20 requests / 5 min, 60k tokens / 10 min, 300k / day), kept
  in memory. IPs are never stored.

## How it works
| Piece | Choice | Why |
|---|---|---|
| App | FastAPI + plain HTML/JS, one process, SQLite | Small, no build step; same shape as Civic Mined |
| Data | Typed tables for facts (with stable keys); markdown for policies and FAQs, with placeholders | Exact edit forms for facts, natural prose for policies, and each fact in one place |
| Retrieval | None: the center's whole knowledge base (~8k tokens) goes in the prompt, cached per center | Nothing can be missed; a new question costs ~35 uncached input tokens |
| Answering | Claude Sonnet 5.5, structured output `{answer, found, sources}` | The server checks every cited section exists, and adds contacts itself |
| Helpers | Claude Haiku 4.5 rewrites follow-ups into standalone questions for the logs, and removes names from logs | Cheap and fast; a regex pass removes phones, emails and addresses first |

Code: `app/` (API), `static/` (UI), `seed/` (center data and test questions), `scripts/` (tools),
`deploy/` (Docker, Caddy, deploy script).

## Run locally
```bash
uv sync
ANTHROPIC_API_KEY=... uv run uvicorn app.main:app --reload
```
Open http://localhost:8000. `data/school.db` is created and seeded on first start; delete it to
start fresh. Settings are listed in `.env.example`.

## Tools
| Command | What it does |
|---|---|
| `uv run python scripts/run_evals.py [--base-url URL]` | Runs all 78 test questions in `seed/*/eval_questions.md` and reports expected vs actual answers |
| `uv run python scripts/kb_lint.py` | Finds values typed into policies that belong in a table, and broken placeholders (no AI) |
| `uv run python scripts/maintain_kb.py --all [--rules-only] [--dry-run]` | Runs the maintenance agent. Schedule documented in KNOWLEDGE_MAINTENANCE.md, not installed |

## Deploy
`DROPLET_IP=<ip> ./deploy/deploy.sh` from a clean checkout. See [docs/DEPLOY.md](docs/DEPLOY.md).

## Docs
[Architecture](docs/ARCHITECTURE.md) · [Contracts](docs/CONTRACTS.md) ·
[Knowledge maintenance](docs/KNOWLEDGE_MAINTENANCE.md) · [Process and phases](docs/PROCESS.md) ·
[Feature docs](docs/features/) · Proposals: [provenance](docs/proposals/PROVENANCE.md),
[center import agent](docs/proposals/CENTER_IMPORT_AGENT.md)
