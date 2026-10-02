# Track D: Admin data editor, history, reset

**Branch:** `track/d-admin-editor` · **Port:** 8104 · **Owns:** `app/routes/admin.py`, `static/admin/data.js`, `static/admin/data.css` (new, imported by data.js), `docs/features/admin-editor.md`

## Goal
Admins can view, add, edit and delete their own center's data, see who changed what, and reset
the center to the seed data. The API is fixed in CONTRACTS §3 ("Admin data").

## Backend: `app/routes/admin.py`
- Every route depends on `session.require_admin`. The center comes **only** from the session.
- Make the table and column whitelist from `app.registry.EDITABLE`:
  - Never put a table or column name from the request into SQL unless it's in the registry.
  - Unknown table → 404.
  - Unknown columns in the body → 400.
  - Missing required columns → 400.
- Light validation by type:
  - `time` matches `HH:MM`, `date` matches `YYYY-MM-DD`.
  - `int` and `money_cents` are integers. The UI sends dollars and converts; the API takes cents.
  - Empty strings become `NULL` for optional columns.
- Ownership checks: every UPDATE and DELETE uses `WHERE id = ? AND center_slug = ?`. If no row
  matches, return 404 (this stops editing another center's rows by guessing ids).
- `centers` is single-row: GET returns the admin's own row, and PUT `/api/admin/data/centers/<slug>`
  only accepts the session's own slug. No create or delete. Don't let `theme_json` be edited
  here (Track I).
- `policies`: `topic` must match `^[a-z0-9_]+$`. A duplicate `(center_slug, topic)` returns 409
  with a clear message.
- **Audit:** in the same transaction as each write, insert into `audit_log` with
  `admin_name = session["display_name"]`, the table, `row_id`, the action, and `before_json` /
  `after_json` (the full row dicts; `null` where not applicable).
- `GET /api/admin/history?limit=50&offset=0`: newest first, own center only.
- `POST /api/admin/reset {confirm: "RESET"}`:
  - Any other body returns 400.
  - Calls `db.load_seed(<slug>)`. The seed dir name equals the slug (CONTRACTS §7).
  - Writes one audit row with `action='reset'`, `table_name='*'`.
  - Doesn't touch sessions, `qa_log` or `audit_log`.

## Frontend: `static/admin/data.js`
The shell (`static/admin.html`, Phase 0) already handles tabs, header and Start over. You export:
- **`mountData(el, session)`:**
  - A list of tables from `GET /api/admin/registry`, shown as a select on mobile and a side list
    on desktop.
  - Picking a table shows its rows: cards on mobile, a table on desktop.
  - Add, edit and delete use a form built from the column metadata:
    - `markdown`/`longtext` → textarea (markdown gets a simple preview toggle)
    - `time`/`date` → native inputs
    - `money_cents` → a dollars input
    - required fields are marked
  - Delete asks for confirmation. Show server errors inline.
  - A **"Reset center to original data"** danger button. It explains what will happen and asks
    the admin to type RESET.
- **`mountHistory(el, session)`:**
  - The audit list: when, who, action, table, row.
  - Expanding an entry shows a before/after diff of the changed fields only.
  - "Load more" pages through older entries.

It must work on mobile at 360px wide. Use the `base.css` tokens. No frameworks.

## Check
- As an admin of center A, edit a fee, then confirm the chat answer changes. That needs Track B;
  otherwise check with `sqlite3`.
- Confirm History shows your name.
- Confirm a parent session gets 403 on `/api/admin/*`.
- Confirm center A can't edit center B's row ids.
- Reset and confirm the seed values come back.
