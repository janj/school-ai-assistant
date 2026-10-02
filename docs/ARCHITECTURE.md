# Architecture

## Overview

```
Browser (static/index.html + chat.js, static/admin.html + admin/*.js)
   │  HTTPS
   ▼
Caddy (TLS for <ip>.sslip.io, compression, security headers)
   │  http://app:8000, X-Forwarded-For
   ▼
FastAPI, 1 uvicorn worker (app/main.py)
   ├─ routes/public.py      /api/centers, /api/session, /api/chat
   ├─ routes/admin.py       /api/admin/data/*, /history, /reset        (admin sessions only)
   ├─ routes/admin_logs.py  /api/admin/logs, /logs/stats                (admin sessions only)
   ├─ session.py   signed cookie → sessions row {role, center_slug, display_name}
   ├─ chat.py      limits → kb render → Claude Sonnet 5.5 → grounding checks → qa_log
   ├─ kb.py        center rows → "[section: id]" text (deterministic, so it caches well)
   ├─ limits.py    per-IP sliding windows, in memory only
   └─ qa_log.py    background thread: regex + Claude Haiku 4.5 scrubbing → qa_log row
   │
   ▼
SQLite (data/school.db on a Docker volume), loaded from seed/<slug>/ on first start
```

Everything runs on one $6/month DigitalOcean droplet (1 vCPU / 1 GB + 1 GB swap), in two
containers (`app`, `caddy`), deployed by hand with `deploy/deploy.sh`. See [DEPLOY.md](DEPLOY.md).

## Center separation

Every content table has `center_slug`. A session is created once with a role and a center, and
`require_session` / `require_admin` are the only source of `center_slug` for any handler. The
chat ignores any center sent in the request. Admin updates and deletes filter on
`id = ? AND center_slug = ?`, so another center's ids return 404. Admin logs and history filter
on the session's center. The prompt contains only the session center's knowledge base, so the
model has no other center's data to leak. All of this was checked by hand in Phase 2.

## Data model

| Kind | Tables | Notes |
|---|---|---|
| Structured facts | `centers`, `contacts`, `hours`, `closures`, `schedule_blocks`, `fees`, `lunch_menu` | Typed columns, edited through forms built from `app/registry.py` |
| Prose | `policies` (topic, title, body_md), `faq` | Markdown; `faq` is for admin answers to unanswered questions (Phase 3) |
| App state | `sessions`, `qa_log`, `audit_log` | Logs store scrubbed text only; no IPs anywhere |

**Why not markdown files?** Admin edits, change history and reset to seed would then work
differently for prose and for facts. **Why not a vector store?** A center's whole knowledge base
is ~7–8k tokens, so it fits in the prompt and is cached, and there is no retrieval step to miss.
Revisit if a center's data grows past ~100k tokens.

Seeds live in `seed/<slug>/` (JSON per table plus `policies/*.md`). `db.load_seed(slug)` is used
both for first start and for an admin's "reset to original data".

## Answer pipeline (`app/chat.py`)

1. `limits.check(ip)`: request count (20 / 5 min), tokens (60k / 10 min, 300k / 24 h), all set by env.
2. The prompt has two cached system blocks: the shared RULES, then the center's knowledge base.
   Today's date and the question go in the user message, so they never break the cache.
3. Sonnet 5.5, effort `low`, structured output `{answer, found, sources}`. A server-side refusal
   fallback is turned on, and the model that actually answered is logged.
4. Grounding checks: unknown section IDs are dropped, and `found=true` with no valid source
   becomes not found. When not found, the server adds the center's main phone/email from the
   database.
5. `qa_log.log_turn` runs in the background and never blocks or breaks the reply.

## Observability
- `docker compose logs app` shows one `chat usage` line per answer (center, model, tokens,
  cache reads/writes).
- The admin Logs tab shows questions, answers, sources, tokens and latency per center, and
  the unanswered ones are the to-do list for improving the data.
- `seed/<slug>/eval_questions.md` is the manual regression list: 21 answerable questions,
  5 unanswerable, 3 follow-ups and 2 in Spanish per center.

## Known limits (POC)
- No real auth: anyone can choose Admin. This was a deliberate demo choice; reset to seed limits
  the damage.
- One worker, so the limits reset on restart. SQLite with a single writer.
- No conversation memory yet: each question stands alone (Phase 3, Track G).
- The same fact can appear in two places (e.g. the registration fee in `fees` and in the
  enrollment policy). If an admin edits only one, the assistant reports the conflict instead of
  picking a value. **Phase 3.0** fixes this with placeholders and a `facts` table (each fact has
  one home), and **Track K** adds a maintenance agent to keep it that way. See
  [KNOWLEDGE_MAINTENANCE.md](KNOWLEDGE_MAINTENANCE.md).
