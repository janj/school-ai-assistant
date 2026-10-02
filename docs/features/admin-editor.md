# Admin data editor, history and reset (Track D)

Admins can view, add, edit and delete their own center's data, see who changed what, and reset the
center to its seed data. Code: `app/routes/admin.py`, `static/admin/data.js`, `static/admin/data.css`.

## How it works

- **Generic CRUD from the registry.** `app.registry.EDITABLE` is the only source of table and
  column names. A table name not in it returns 404; unknown body columns return 400. Nothing from
  the request is put into SQL unless it came out of the registry. Values always go in as bound
  parameters.
- **Center lock.** The center comes only from `session.require_admin`. Every UPDATE and DELETE
  uses `WHERE id = ? AND center_slug = ?`; a row from another center looks like a missing row
  (404), so guessing ids reveals nothing. The row is read with the same filter before any write.
- **Validation by column type.** `time` is `HH:MM`, `date` is a real `YYYY-MM-DD`, `int` and
  `money_cents` must be integers (the UI converts dollars to cents). Empty strings become `NULL`;
  a required column that ends up empty returns 400. Optional `int` (sort_order) falls back to 0
  because the column is `NOT NULL DEFAULT 0`.
- **Updates merge.** A PUT body is laid over the current row, so partial bodies work and required
  columns are still enforced on the result.
- **Special cases.** `centers` is one row keyed by slug (own slug only, no create/delete,
  `theme_json` is not in the registry so it can't be edited). `policies.topic` must match
  `^[a-z0-9_]+$`; a duplicate topic returns 409. `faq.created_by` is set from the session.
- **Audit.** Each write inserts an `audit_log` row in the same transaction, with the admin's
  display name and the full before/after row dicts (`null` where not applicable).
  History is newest first, own center only.
- **Reset.** `POST /api/admin/reset {confirm:"RESET"}` calls `db.load_seed(<slug>)` and then
  writes one `action='reset'`, `table_name='*'` audit row. Sessions, `qa_log` and `audit_log` are
  untouched.

## Front end

`mountData` shows a select (mobile) or a side list (desktop) of tables, rows as cards (mobile) or
a table (desktop, switched by CSS at 760px), and a form generated from column metadata
(textarea for `longtext`/`markdown` with an Edit/Preview toggle, native time/date inputs, a dollars
input for `money_cents`, required fields starred). Delete uses an inline "Yes, delete" confirmation.
Server errors show inline. The "Reset center to original data" danger zone needs RESET typed.
`mountHistory` lists entries with who/when/action/target; expanding one shows only the changed
fields, before and after. "Load more" pages by offset.

## Decisions beyond the brief

- Reset audit row has no before/after (no cheap full snapshot); the entry just says the center was reset.
- If only the placeholder `seed/_example` exists (its dir name is not its slug), reset uses it.
  With real seeds the dir name equals the slug as in CONTRACTS section 7.
- History returns the raw `before_json`/`after_json` strings; the client parses them.
- The editor row `id` for `centers` is the slug, so the same client code works for every table.
- `data.css` is injected by `data.js` with a `<link>` (CSS module imports aren't portable).
- The markdown preview is a tiny built-in renderer (headings, bold/italic, bullets), built with DOM
  nodes, not `innerHTML`.
