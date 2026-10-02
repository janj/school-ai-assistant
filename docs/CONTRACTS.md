# Contracts

These are the shared boundaries between parallel tracks. **Tracks may not change anything in this
file.** If a contract blocks you, stop and report it in your summary. The plan and file ownership
are in [PROCESS.md](PROCESS.md).

## 1. Running locally

```
uv sync
ANTHROPIC_API_KEY=$(cat claude-key) uv run uvicorn app.main:app --reload --port 8000
```

- On startup, `init_db()` creates `data/school.db` and loads every `seed/<slug>/` directory that
  isn't in the database yet.
- `seed/_example` loads only when no real seed exists.
- To start over from a clean database, delete `data/school.db`.
- `.env` is supported (see `app/config.py` for every setting). Never commit `.env` or `claude-key`.

## 2. Session and center lock

- The cookie `sa_session` holds a signed session id. Role, center and display name live in the
  `sessions` row.
- Dependencies (in `app/session.py`):
  - `require_session(request) -> {id, role, center_slug, display_name}`, or 401.
  - `require_admin(...)`: the same, or 403 if the role isn't admin.
- **Every handler gets `center_slug` from these dependencies and nowhere else.** Never accept a
  center from the request body, the query or a header.

## 3. HTTP API

All bodies are JSON. Errors are `{"detail": str}` (FastAPI's default), unless noted.

### Public (Phase 0, already implemented)
| Method | Path | Body → Response |
|---|---|---|
| GET | `/api/centers` | → `[Center]` |
| POST | `/api/session` | `{role: "parent"\|"admin", center_slug, display_name?}` → `Session`. Admins must give a display name (400 if not) |
| GET | `/api/session` | → `Session`, or 401 |
| DELETE | `/api/session` | → `{ok: true}` (the "start over" control) |
| POST | `/api/chat` | `{message, conversation_id?}` → `ChatAnswer` |

- `Center` = `{slug, name, tagline, main_phone, main_email, theme: {primary, accent, background, font, logo_text}}`
- `Session` = `{role, display_name, center: Center}`
- `ChatAnswer` = `{answer: str, found: bool, sources: [section_id], contact: {phone, email} | null, conversation_id: str | null}`
  - `answer` is plain text with light markdown allowed: `**bold**`, lists, line breaks.
  - `contact` is non-null exactly when `found` is false. The server fills it from `centers.main_phone` / `main_email`.
  - `conversation_id` is echoed back. Follow-ups in the same conversation get the last 4 turns as
    context (Phase 3, `app/history.py`; history is in memory only and tied to the session).
- Chat errors (plus `400 {detail, kind: "turn_cap"}` after 8 turns in one conversation):
  - `400` for an empty message or one over 1,000 characters.
  - `401` when there's no session.
  - `429 {detail, kind: "rate" | "budget"}`.
  - `503` when the model call fails.

`chat.answer(session, message, conversation_id, client_ip) -> ChatAnswer` raises
`limits.LimitExceeded(kind, detail)` or `chat.UpstreamError`. The route maps these to HTTP codes.

### Admin data (Track D). All need `require_admin`; the center comes from the session
| Method | Path | Body → Response |
|---|---|---|
| GET | `/api/admin/registry` | → `app.registry.EDITABLE` as JSON (`columns` as `{name, type, label, required}`) |
| GET | `/api/admin/data/{table}` | → `[row]` for the session's center (`centers` returns the single own row) |
| POST | `/api/admin/data/{table}` | `{...columns}` → the created row (not allowed for `centers`) |
| PUT | `/api/admin/data/{table}/{id}` | `{...columns}` → the updated row (`centers` is keyed by slug and only allows the own slug) |
| DELETE | `/api/admin/data/{table}/{id}` | → `{ok: true}` (not allowed for `centers`) |
| GET | `/api/admin/placeholders` | → `[{token, value, group}]`: every placeholder available to this center (Phase 3.0) |
| POST | `/api/admin/preview` | `{text}` → `{rendered, invalid: [token]}`: placeholders filled in as the assistant sees them (Phase 3.0) |
| GET | `/api/admin/history?limit=&offset=` | → `[audit_log row]`, newest first |
| POST | `/api/admin/reset` | `{confirm: "RESET"}` → `{ok: true}`. Calls `db.load_seed(<seed dir for the center>)` and writes an audit row with `action='reset'` |

- `{table}` must be a key of `registry.EDITABLE`; anything else returns 404.
- Every write records `audit_log(admin_name = session.display_name, before_json, after_json)`.
- **Keys (Phase 3.0).** `contacts`, `hours`, `fees` and `facts` rows have a `key`:
  - required on create, and must match `^[a-z0-9_]+$` (400 otherwise);
  - unique per center (409 on a duplicate);
  - can't be changed afterwards (400);
  - can't be deleted while a policy or FAQ uses it (409, naming who uses it).
- **Placeholders (Phase 3.0).** `policies.body_md` and `faq.answer` are checked on save. An
  unknown or malformed placeholder returns 400 and lists them.
- The seed directory name for a center is the same as its slug (see §7).

### Admin logs (Track E). All need `require_admin`; center comes from the session
| Method | Path | Response |
|---|---|---|
| GET | `/api/admin/logs?found=all\|false\|true&limit=&offset=` | → `[qa_log row]`, newest first |
| GET | `/api/admin/logs/stats` | → `{total, unanswered, open_unanswered, last_7_days, tokens: {input, output, cache_read}}` |
| GET | `/api/admin/logs?status=open` | → unanswered rows not yet answered as an FAQ (Phase 3, Track H) |
| POST | `/api/admin/logs/{id}/answer` | `{question, answer}` → the new `faq` row. Placeholders are validated like policies; 409 if already answered |

### Data issues (Phase 3, Track K). All need `require_admin`; center comes from the session
| Method | Path | Body → Response |
|---|---|---|
| GET | `/api/admin/issues?status=open` | → `[kb_issues row]` |
| POST | `/api/admin/issues/{id}/status` | `{status: resolved\|dismissed}` → the row |
| POST | `/api/admin/issues/run` | `{ai: bool}` → run summary. AI runs are limited to 1 per 10 minutes per center (429) |
| GET | `/api/admin/issues/auto-fixes` | → `audit_log` rows written by `kb-maintenance-agent` |

## 4. Knowledge-base rendering (Track B owns `app/kb.py`)

- `render_center_kb(center_slug) -> str` returns the center's whole knowledge base as text.
- `section_ids(center_slug) -> set[str]` returns exactly the IDs present in that text.
- Each section starts with the line `[section: <id>]`. The IDs are:

| ID | Source |
|---|---|
| `center` | `centers` row (name, address, main phone/email, website) |
| `contacts` | `contacts` |
| `hours` | `hours` |
| `closures` | `closures` (the prompt also gives today's date so the model can say "next closure") |
| `schedule` | `schedule_blocks`, grouped by age group |
| `fees` | `fees` (amounts shown as dollars) |
| `lunch_menu` | `lunch_menu` |
| `facts` | `facts` (label: value), Phase 3.0 |
| `policy:<topic>` | one per `policies` row |
| `faq:<id>` | one per `faq` row (Track H fills these; B renders whatever rows exist) |

Output must be deterministic (stable ordering, no timestamps inside the KB text), so the prompt
cache only changes when the data changes.

### Placeholders (Phase 3.0, `app/placeholders.py`)
Policy bodies and FAQ answers are filled in while the knowledge base is built. The model never
sees `{{...}}`.

| Token | Renders | Fields (first is the default) |
|---|---|---|
| `{{fee:key}}` | `$75.00` | `amount`, `name`, `period`, `notes` |
| `{{contact:key}}` | `Rosalind Vega, RN` | `name`, `phone`, `email`, `position` |
| `{{hours:key}}` | `6:30 AM - 6:00 PM` / `Closed` | `span`, `open`, `close`, `days` |
| `{{fact:key}}` | the value | `value`, `label` |
| `{{center:field}}` | the center row field | `name`, `main_phone`, `main_email`, `address`, `website`, `tagline` |

A placeholder with no matching row renders as `(not listed)` and logs a warning, so the model
never sees a gap it might fill by guessing.

**Stable-key assumption (POC).** Keys are unique per center and can't be changed after creation,
and rows in use can't be deleted. All of that is enforced in code. Deleting a row and re-creating
it under a different key is not prevented. Production would add key pickers, a shared key
vocabulary across centers, and migrations for renames.

## 5. Logging hook (Track E owns `app/qa_log.py`)

B calls this once per successful answer, after the response is built:

```python
qa_log.log_turn(center_slug=..., session=..., conversation_id=..., question=..., answer=...,
                found=..., sources=[...], model=..., usage={input_tokens, output_tokens,
                cache_read_tokens, cache_write_tokens}, latency_ms=..., rewritten_query=None)
```

- It must not block the response noticeably: PII scrubbing runs on a background thread.
- It must never raise.
- It stores only scrubbed text and never stores an IP.

## 6. Front end

- `static/base.css`: the token names (`--brand-primary`, `--brand-accent`, `--brand-bg`,
  `--brand-font`, `--surface`, `--text`, `--text-muted`, `--border`, `--danger`, `--ok`,
  `--radius`, `--space`) are fixed. Track C may change the values and add rules.
- To theme a page from `center.theme`, set the `--brand-*` variables on `document.documentElement`.
  Track C applies `primary`/`accent`/`background` in Phase 1; Track I does the full theming.
- `static/admin.html` is the admin shell. Tab modules are ES modules:
  - `static/admin/data.js` exports `mountData(el, session)` and `mountHistory(el, session)` (Track D).
  - `static/admin/logs.js` exports `mount(el, session)` (Track E).
- Pages: `/` is `static/index.html` (picker + chat, Track C). `/admin` is `static/admin.html`.
  The chat UI links to `/admin` when the role is admin.
- Every page has a visible **Start over** control that calls `DELETE /api/session` and then goes to `/`.
- Mobile first: works at 360px wide, no sideways scrolling, tap targets ≥ 40px.

## 7. Seed format (Track A owns `seed/`)

There is one directory per center: `seed/<slug>/`. The directory name must equal `center.json`'s `slug`.

| File | Shape (one object per row; columns as in `app/schema.sql`, minus `id`/`center_slug`) |
|---|---|
| `center.json` | `{slug, name, tagline, address, main_phone, main_email, website, theme: {primary, accent, background, font, logo_text}}` |
| `contacts.json` | `[{key, name, position, phone, email, sort_order}]`. Key by role (`director`, `nurse`), not by person |
| `hours.json` | `[{key, days, open_time, close_time, notes}]`. Times are 24h `"HH:MM"`; `null` means closed |
| `closures.json` | `[{start_date, end_date, name, notes}]`. ISO dates; `end_date` is `null` for one day. Covers 2026-08 through 2027-07 |
| `schedule.json` | `[{age_group, start_time, end_time, activity}]` |
| `fees.json` | `[{key, category, name, amount_cents, period, notes}]` |
| `facts.json` | `[{key, label, value, notes}]`: reused facts with no other table home (fever threshold, grace period, …) |
| `lunch.json` | `[{day, meal, items, notes}]` |
| `policies/<topic>.md` | The first line is `# Title`, then a markdown body. Values that have a home elsewhere use placeholders or "see Fees"-style pointers ([KNOWLEDGE_MAINTENANCE.md](KNOWLEDGE_MAINTENANCE.md) §2). `scripts/kb_lint.py` must report 0 failing findings |
| `eval_questions.md` | Not loaded. Manual check list: questions with expected answers, plus ones the data can't answer |

**Required policy topics:** `late_pickup`, `items_from_home`, `enrollment`, `birthdays`,
`illness_exclusion`, `lunch_info`, `arrival_dropoff`. Optional: `general`, `payments`.

All seed data is made up. Use `555-01xx` phone numbers and `.test` email domains.
