# School AI Assistant — Phased Process

This document holds the goals, decisions and phased plan for the POC, and tracks parallel work.
Each track is written so that one Sonnet subagent can take it. The agent works on its own worktree
and branch (`track/<letter>-<slug>`), and ends with a change summary that we review before merging.

**Status key:** `todo` · `active` · `review` · `merged` · `blocked`

---

## 1. Goals

An AI chat client, open to anyone, that answers questions about **one childcare center**. Every
answer comes only from that center's data. Admins can edit the data. It is hosted on a
DigitalOcean droplet and deployed by hand from the operator's machine.

| # | Requirement | Where it lands |
|---|---|---|
| R1 | Mocked session: pick **parent/admin** and **center**; reset control on every screen | Track C |
| R2 | Admins change/add data | Track D |
| R3 | Mobile friendly | Track C (and D/E for the admin pages) |
| R4 | Per-IP request limit + token budget | Track B |
| R5 | Session locked to its center; center data kept separate in storage and prompts | Phase 0 contract, Track B |
| R6 | Nothing made up; "not found" answers give the center's real phone/email | Track B |
| R7 | Data store choice justified (structured + unstructured) | §3, `docs/ARCHITECTURE.md` |
| R8 | Every Q/A logged with PII removed; admins see their own center's logs only | Track E |
| R9 | README (1 page) + `docs/` (architecture + feature docs) | Every track + Phase 2 |
| — | No tests (POC) | — |

**Nice-to-haves** (Phase 3): center themes · voice · admin change history (cheap, so done in
Phase 1, Track D) · answer in the question's language (one prompt rule, so done in Phase 1,
Track B) · conversational context with follow-up rewriting · admin queue of unanswered questions
that become knowledge-base entries · reset data to seed (cheap, so done in Phase 1, Track D).

## 2. Decisions (resolved with the operator, 2026-10-01)

| Topic | Decision |
|---|---|
| Admin access | Open: anyone can choose admin. Admins type a display name, used for the change history. Admins can reset their center's data to the seed |
| Centers | Two made-up centers, each with its own branding/theme. Seed data is loosely based on the Albuquerque family handbook, but none of its real data is used |
| Repo | `github.com/janj/school-ai-assistant`, public, created with `gh` (the local folder keeps its original spelling) |
| Deploy | Done by hand from the operator's machine (`deploy/deploy.sh`: rsync + ssh + `docker compose up`). No CI deploy |
| Review | Agents deliver branches with a written summary. We review and merge locally |
| IPs | **Never stored.** Rate limiters keep IP keys in memory only |
| Admin log view | Limited to the session's own center |
| Hosting | A **separate** $6/month droplet (1 vCPU / 1 GB), not shared with Civic Mined. Hostname is `<droplet-ip>.sslip.io`, with HTTPS certificates issued automatically by Caddy |

## 3. Architecture choices and why

**Stack: Python 3.12, FastAPI, `uv`, the `anthropic` SDK called directly, plain HTML/CSS/JS, Docker Compose + Caddy.**
This matches Civic Mined, so the operator already knows how it runs and how to fix it. There is no
build step for the front end.

**Data store: one SQLite file (`data/school.db`) holding typed tables plus markdown policy rows.**
- *Structured tables* (directory, hours, closures, daily schedule, fees, lunch menu): these facts
  are exact and get edited one row at a time. A table gives admins a form instead of free text,
  and the model reads tidy, precise values.
- *Unstructured policy rows* (`policies`: late pickup, items from home, enrollment, birthdays,
  illness/keep-home criteria, lunch info, general): these are naturally prose. They are stored as
  markdown in a table, not as `.md` files, so admin edits, change history and reset all work the
  same way for every kind of data.
- *Why SQLite and not the Postgres cluster:* there is one writer, the data is small, backup is one
  file, and the POC doesn't depend on Civic Mined's production database.
- *Center separation:* every tenant row carries `center_slug`. The center is **never read from the
  request**. It always comes from the server-side session (§4.2), the same principle as Civic
  Mined's tenant binding.

**Retrieval: none. The center's whole knowledge base goes into the prompt, with caching.**
A center's KB is estimated at ~8–20k tokens. It is rendered into one system-prompt block with a
cache breakpoint: the rules block comes first, then the KB block. Each center gets its own cached
prefix. An admin edit changes the text, which naturally invalidates the cache. Without a retrieval
step, retrieval can't miss, and the "nothing made up" rule gets simpler: the model can only cite
section IDs that are actually in the prompt.

**Grounding (R6):** the model returns structured output `{answer, found, sources[]}`, where
`sources` are section IDs from the KB (e.g. `contacts`, `policy:late_pickup`). The server checks
that every ID exists. When `found=false`, **the server** (not the model) adds the center's main
phone/email from the database, so the contact details can't be made up.

**Models:** `claude-sonnet-5-5` writes answers. `claude-haiku-4-5-20251001` removes PII and (in
Phase 3) rewrites follow-up questions.

## 4. Shared boundaries (finished in Phase 0, before any track starts)

Phase 0 writes these into `docs/CONTRACTS.md` and the stub code. **Tracks may not change a
contract.** If one needs a change, the agent stops and reports it.

### 4.1 Repo layout and file ownership

```
app/
  main.py            FastAPI app, mounts routers, static files          [P0]
  config.py          env settings (API key, limits, model IDs)          [P0]
  db.py              connection, schema init, seed load/reset           [P0 stub → D owns reset]
  schema.sql         all tables                                         [P0]
  session.py         mocked session: create/read/clear, center lock     [P0]
  kb.py              render_center_kb(slug) -> str with section IDs     [B]
  chat.py            answer pipeline, prompt caching, grounding         [B]
  limits.py          per-IP request + token budget (memory only)        [B]
  qa_log.py          log_turn(...), PII scrub, queries for admin view   [E]
  registry.py        editable-table metadata for the admin editor       [P0 → D]
  routes/public.py   /api/session, /api/centers, /api/chat              [P0 stub → B]
  routes/admin.py    /api/admin/data/*, /api/admin/reset, /history      [D]
  routes/admin_logs.py /api/admin/logs*                                 [E]
seed/<center-slug>/
  center.json  contacts.json  hours.json  closures.json  schedule.json
  fees.json  lunch.json  policies/<topic>.md  eval_questions.md         [A]
static/
  base.css           design tokens as CSS variables (theme hooks)       [P0 → C]
  index.html chat.js            picker + chat UI                        [C]
  admin.html                    tab shell: Data | History | Logs        [P0]
  admin/data.js                 data editor tab                         [D]
  admin/logs.js                 logs tab                                [E]
deploy/  Dockerfile  docker-compose.yml  Caddyfile  deploy.sh           [F]
docs/    ARCHITECTURE.md  CONTRACTS.md  PROCESS.md  DEPLOY.md  features/<track>.md
```

### 4.2 Session

- `POST /api/session {role: "parent"|"admin", center_slug, display_name?}` sets a signed,
  HttpOnly cookie that points to a `sessions` row.
- `GET /api/session` returns the current session. `DELETE /api/session` resets it (the "start
  over" control).
- `require_session()` and `require_admin()` are FastAPI dependencies. Every handler gets
  `center_slug` **only** from these.

### 4.3 Tables (exact columns are fixed in `schema.sql` in Phase 0)

`centers` (slug, name, tagline, address, main_phone, main_email, website, theme_json) ·
`contacts` · `hours` · `closures` · `schedule_blocks` · `fees` · `lunch_menu` ·
`policies` (topic, title, body_md) · `faq` (question, answer, created_by; filled by Phase 3) ·
`sessions` · `qa_log` · `audit_log` (admin_name, table, row_id, action, before_json, after_json, at).

### 4.4 Chat API

`POST /api/chat {message, conversation_id?}` returns
`{answer, found, sources[], contact?: {phone, email}, conversation_id}`.
Errors: `429 {detail, kind: "rate"|"budget"}` · `400` for an empty message or one over
1,000 characters · `503` when the upstream model fails.

### 4.5 Logging hook

B calls `qa_log.log_turn(center_slug, session_id, conversation_id, question, answer, found,
sources, usage, latency_ms)` after each answer. E implements it (removes PII asynchronously and
stores only scrubbed text). Until E lands, the stub does nothing.

### 4.6 Seed format

The JSON shapes for each file are fixed in `CONTRACTS.md`. They match the table columns one to
one, so `db.load_seed(slug)` stays a plain loader.

## 5. Phases and tracks

### Phase 0 — Foundations (operator + Opus, serial)  `merged`
Create the repo; add `.gitignore` (done); create the skeleton in §4.1 with stubs; write
`schema.sql`, `CONTRACTS.md`, session handling, `registry.py` metadata, the `base.css` token
names and the admin tab shell. **Exit:** the app runs locally, you can pick a session, and
`/api/chat` returns a stub reply.

### Phase 1 — MVP end to end (parallel Sonnet tracks)

| Track | Scope | Depends on | Status |
|---|---|---|---|
| **A · Seed data** | Two made-up centers covering all 11 topics. They must differ clearly (hours, fees, policies). Include `eval_questions.md` per center: ~20 questions with expected answers, plus ~5 that the data can't answer | P0 | merged |
| **B · Chat backend** | `kb.py` rendering with section IDs; `chat.py` with Sonnet, two cache breakpoints (rules, KB), structured output, source checking, server-added contact on `found=false`, answer in the question's language; `limits.py` (defaults: 20 req / 5 min, 60k tokens / 10 min, 300k tokens / day per IP; settable by env) | P0 (can use A's seed when ready) | merged |
| **C · Frontend** | Picker (role + center + admin name), chat UI (message bubbles, sources shown as chips, not-found contact card, error states per §4.4), reset control on every view, mobile-first layout | P0 | merged |
| **D · Admin data editor** | Generic CRUD driven by `registry.py` (tables and markdown policies), `audit_log` written on every change, History tab, "reset center to seed" with a confirm step | P0 | merged |
| **E · Q/A logging** | `log_turn`, PII scrub (regex for phones/emails, then Haiku for people's names; staff names from the directory are kept), Logs tab filtered by center with an "unanswered only" filter | P0 | merged |
| **F · Deploy** | Dockerfile, compose (app + Caddy, SQLite on a volume), Caddyfile, `deploy.sh` run by hand from this machine, `docs/DEPLOY.md` covering droplet setup from scratch | P0 | merged |

Track briefs: `docs/tracks/` (start with `_common.md`). Each track's deliverable: its branch, a feature doc at `docs/features/<track>.md`, and a summary
(what changed, decisions made, anything left open). **Tracks touch only files they own.**

### Phase 2 — Integrate and ship (operator + Opus)  `merged`
Merge in the order A → B → E → C → D → F. Run every `eval_questions.md` question by hand, fix
gaps, write the 1-page `README.md` and `docs/ARCHITECTURE.md`, deploy and do a live check.

### Phase 3.0 — Single source of truth for facts (operator + Opus, serial)  `merged`

**Problem (found in Phase 2):** policy prose repeats facts that also live in tables: about 18–22
per center (fees, contact phones/emails, times). When an admin edits the fees table, the copy in
the policy goes stale, and the assistant reports a conflict instead of answering. See
[KNOWLEDGE_MAINTENANCE.md](KNOWLEDGE_MAINTENANCE.md).

**Decision:** every fact has exactly one home.
- Prose that needs a value uses a **placeholder** (option 4).
- Prose that doesn't need it **points to the section** (option 1).

This changes shared contracts (schema, seed format, `kb.py`), so it is done serially before the
parallel Phase 3 tracks start, the same way as Phase 0.

**Stable-key assumption (documented POC assumption):**
- Keyed rows have a `key` that is unique per center, matches `^[a-z0-9_]+$`, is set at creation,
  and **cannot be changed afterwards**.
- The POC enforces this cheaply:
  - a `UNIQUE(center_slug, key)` constraint;
  - the API rejects key changes;
  - deleting a row that a policy or FAQ uses is blocked with 409.
- Not covered: deleting a row and re-creating it under a different key.
- Production would add key pickers, shared key vocabularies across centers, and migration
  tooling for renames.

**Scope**
1. **Schema**
   - Add `key` to `fees`, `contacts`, `hours`.
   - New table `facts(id, center_slug, key, label, value, notes)` for reused facts that have no
     table home (e.g. the fever threshold or the late-pickup grace period).
   - All four tables get `UNIQUE(center_slug, key)`.
2. **Placeholder grammar.** The form is `{{type:key}}` or `{{type:key.field}}`, filled in by
   `kb.py` when it builds the knowledge base:

   | Type | Default | Fields |
   |---|---|---|
   | `fee` | amount (`$75.00`) | `.name` `.period` |
   | `contact` | name | `.phone` `.email` `.position` |
   | `hours` | `6:30 AM - 6:00 PM` | `.open` `.close` |
   | `fact` | value | `.label` |
   | `center` | — | `.name` `.main_phone` `.main_email` `.address` `.website` |

   - It applies to `policies.body_md` and `faq.answer`.
   - A placeholder with no matching row renders as `(not listed)` and logs a warning, so the
     model never sees a gap it might fill by guessing.
   - The knowledge base also gets a `facts` section, so facts can be asked about directly.
3. **Admin editor**
   - `key` is a required field on create and read-only afterwards.
   - The `facts` table is editable.
   - Saving a policy or FAQ with an unknown placeholder returns 400 and lists the bad ones.
   - Deleting a row that is in use returns 409 and names the policies that use it.
   - A **filled-in preview** (`POST /api/admin/preview`), and a placeholder picker listing the
     available keys.
4. **Seed rewrite.**
   - Add keys to every keyed row, and add `facts.json`.
   - Replace each duplicated literal in the policies with a placeholder or a "see Fees / see
     Directory" pointer.
5. **`scripts/kb_lint.py`.** A predictable, non-AI report of literal values in policies and
   FAQs that match a keyed value, plus broken placeholders. It is the base for Track K.
6. **Docs.** Update `CONTRACTS.md` (§3 admin API, §4 sections, §7 seed format, the key
   assumption), `ARCHITECTURE.md` and `docs/features/`.

**Exit criteria**
- `kb_lint.py` reports **0** duplicated literals and **0** broken placeholders for both centers.
- All 62 eval questions still pass.
- Editing `fee:registration` changes the enrollment policy's filled-in text and the next chat
  answer, with no conflict.
- Deleting a fee that is in use returns 409.
- Changing a key returns 400.

### Phase 3 — Nice-to-haves (parallel Sonnet tracks)

| Track | Scope | Owns | Status |
|---|---|---|---|
| **G · Conversation context** | Client-minted `conversation_id`; raw history kept **in memory only** (30-min idle window, last 4 turns, 8-turn cap); Haiku rewrites follow-up questions | `chat.py` history section, `chat.js` thread state | todo |
| **H · Unanswered → KB** | Logs tab action "answer this" creates a `faq` row that is shown in the KB; changes go to the audit log | `admin/logs.js`, `faq` rendering in `kb.py` | todo |
| **I · Center themes** | `theme_json` → CSS variables, logo/wordmark, favicon per center | `base.css`, a theme loader | todo |
| **J · Voice** | Web Speech API mic input + optional read-aloud, with feature detection | `static/voice.js` + one hook in `chat.js` | todo |

| **K · Knowledge maintenance agent** | Scheduled and on-demand agent. It fixes clear-cut issues itself and files everything else in a "Data issues" review queue. Spec: [KNOWLEDGE_MAINTENANCE.md](KNOWLEDGE_MAINTENANCE.md) §3 | `app/maintenance.py`, `scripts/maintain_kb.py`, `kb_issues` table, `static/admin/issues.js`. The cron schedule is **documented only, not installed** (operator decision) | todo |

- All Phase 3 tracks start after Phase 3.0 merges.
- G and J both touch `chat.js`. J only adds a hook that Phase 0 or G defines, so G merges first.
- H and K both add admin review queues. K's "Data issues" tab follows H's pattern, so H merges
  first. K reuses `scripts/kb_lint.py` from 3.0.

## 6. Subagent rules (included in every brief)

1. Work only in your worktree and branch. Only edit files your track owns (§4.1).
2. Don't change `schema.sql`, `CONTRACTS.md` or the API shapes. If one blocks you, stop and report.
3. Never read, print or commit `claude-key` or `.env`. Use `ANTHROPIC_API_KEY` from the environment.
4. No tests (POC). Do run the app locally to check that your track works.
5. Finish with: commit(s) on your branch, `docs/features/<track>.md`, and a summary listing files
   changed, decisions made, open questions and how to try it.

## 7. Open items

- [x] Droplet created and bootstrapped: 162.243.171.212 → https://162-243-171-212.sslip.io
- [ ] Confirm the DO Cloud Firewall allows 80/443 (verified on first deploy).
