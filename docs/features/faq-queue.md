# Unanswered questions to FAQ (Track H)

Admins turn questions the assistant couldn't answer into knowledge-base entries, so the next
parent who asks gets an answer.

## How it works
- **Logs tab** (`static/admin/logs.js`): unanswered cards that aren't resolved yet show an
  **Answer this** button. It opens an inline form: the question (prefilled, editable), an answer
  textarea, a placeholder picker (`GET /api/admin/placeholders`, inserted at the cursor) and a
  server-side preview (`POST /api/admin/preview`). Resolved cards show an "Answered in FAQ #n" badge.
- **Open filter** = `found = 0 AND resolved_faq_id IS NULL`. It is the default when the stats say
  there are open items. The stats strip has an "open unanswered" tile.
- **API** (`app/routes/admin_logs.py`):
  - `GET /api/admin/logs?status=open` (the `found=` filter still works).
  - `POST /api/admin/logs/{id}/answer {question, answer}`: in one transaction inserts a `faq` row
    (`created_by` = admin's display name, `source_qa_id` = log id), sets `qa_log.resolved_faq_id`
    and writes an `audit_log` row (`faq`, `create`) through `admin._audit`. Returns the FAQ row.
  - `GET /api/admin/logs/stats` adds `open_unanswered`.
- Nothing changes in chat: `kb.py` already renders `faq` rows as `[section: faq:<id>]` with
  placeholders resolved.

## Decisions
- Answers go through `placeholders.invalid`, so an unknown placeholder returns 400 (same message as
  policy saves). Both fields are required (400). Another center's log id returns 404.
- Answering a log that already has an FAQ returns 409, so a double click can't create duplicates.
- The stored question is already scrubbed of personal info; the form asks admins to generalize it.
- The placeholder tools are copied from `data.js`, not imported, to keep tracks independent.
- Also fixed in `logs.css`: `[hidden]` was overridden by `display:block` on "Load more".
