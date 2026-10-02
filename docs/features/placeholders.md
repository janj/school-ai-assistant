# Placeholders and the facts table (Phase 3.0)

Every fact has one home. Policy and FAQ text refer to values through placeholders, which are
filled in when the knowledge base is built. Editing a fee changes every policy that mentions it.

## Pieces
- **Keys:** `contacts`, `hours`, `fees` and the new `facts` table have a `key`. It is unique per
  center, matches `^[a-z0-9_]+$`, can't be changed after creation, and a row can't be deleted
  while it's in use. Contacts are keyed by **role** (`nurse`, `director`), so a staff change keeps
  every reference working.
- **`app/placeholders.py`:** parsing, `render()` (unresolved → `(not listed)` plus a log
  warning), `invalid()` (for save-time validation), `references()` (for delete protection) and
  `catalog()` (for the picker). The grammar is in CONTRACTS §4.
- **`app/kb.py`:** fills in policy bodies and FAQ answers, and adds a `facts` section.
- **Admin API:** key rules, placeholder validation on save, 409 on deleting a row in use,
  `GET /placeholders`, `POST /preview`.
- **Editor:** policy bodies and FAQ answers get an "Insert placeholder…" picker and a preview
  rendered by the server. Key fields are read-only after creation. Negative amounts (discounts)
  are allowed.
- **`scripts/kb_lint.py`:** non-AI duplicate and broken-placeholder report (exit 1 on failing
  findings).
- **Migration:** `db._migrate` adds the `key` columns to older databases and re-seeds affected
  centers. In this POC, admin edits made before Phase 3.0 are lost; the audit log is kept.

## Results
- **Lint:** before, 16 failing findings plus 11 to review. After, 0 failing and 1 to review: "24
  hours" in the fever rule, a different fact that happens to share a value. Correct as is.
- **Drift fixed by the rewrite:** the policies disagreed with the schedule on breakfast, nap and
  PM snack times. They now point to the daily schedule.
- **Evals:** all 62 questions still answer correctly (e.g. "20 minutes late" still works out to
  $15.00 from the grace-period and fee rules).
- **Edit propagation:** after changing the registration fee to $99.00, the chat answered "$99.00"
  with the enrollment policy cited, and no conflict.

## Known remaining duplication
The center's main phone/email are stored on `centers` *and* on the front-desk directory row
(the lint reports them as ambiguous candidates). That duplication is between two tables, not in
prose. Left for Track K to flag. A real fix would let the center row point to a contact key.
