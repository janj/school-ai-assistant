# Track H: Unanswered questions → knowledge base

**Branch:** `track/h-faq-queue` · **Port:** 8112 · **Owns:** `app/routes/admin_logs.py`, `static/admin/logs.js`, `static/admin/logs.css`, `docs/features/faq-queue.md`

## Goal
Admins turn questions the assistant couldn't answer into knowledge-base entries. The next parent
who asks gets an answer.

## Backend (`app/routes/admin_logs.py`)
- `GET /api/admin/logs`: add `status=open` as a filter. "Open" means `found = 0 AND
  resolved_faq_id IS NULL`. Keep the existing `found=` filter working.
- `POST /api/admin/logs/{id}/answer` with `{question, answer}`:
  - Requires an admin session. The log row must belong to the session's center, else 404.
    Both fields are required.
  - **The answer is checked for placeholders** with `app.placeholders.invalid(answer, ctx)`.
    It returns 400 listing unknown ones, the same rule as policy saves (CONTRACTS §3).
  - In one transaction:
    - insert a `faq` row (`created_by` = admin's display name, `source_qa_id` = log id);
    - set `qa_log.resolved_faq_id`;
    - write an `audit_log` row (`table_name='faq'`, `action='create'`) in the same format
      as `app/routes/admin.py` `_audit`.
  - Returns the created FAQ row.
  - Prefill note: the stored question is already scrubbed of personal info. Admins should
    generalize it ("Do you offer swim lessons?").
- `GET /api/admin/logs/stats`: add `open_unanswered`.

`kb.py` already renders `faq` rows as `[section: faq:<id>]` with placeholders filled in, so
**nothing changes in chat**. Confirm it end to end.

## Frontend (`static/admin/logs.js`)
- At the `// HOOK(faq)` spot on unanswered, unresolved cards: an **"Answer this"** button.
  It opens an inline form with:
  - the question, prefilled and editable;
  - an answer textarea;
  - the hint "Insert placeholders for fees, contacts and times; don't type values that live
    in another table."
  - a **placeholder picker** (`GET /api/admin/placeholders`, insert at the cursor) and a
    **preview** (`POST /api/admin/preview`). Copy the approach in `static/admin/data.js`
    `placeholderTools`; don't import across tracks.
- Resolved cards show a "Answered in FAQ #n" badge.
- Add an **"Open"** filter (unanswered and not yet answered) and make it the default when
  there are open items.
- The stats strip shows open unanswered items.
- Mobile-friendly at 360px wide; test desktop width too.

## Check
Real API:
1. As a parent, ask something the data can't answer, e.g. "Do you offer swim lessons?".
2. As an admin, answer it, including a placeholder such as `{{contact:front_desk.phone}}`.
3. Confirm the next parent question gets `found=true` citing `faq:<id>`, with the placeholder
   filled in.
4. Confirm the History tab shows the FAQ creation.
5. Confirm a bad placeholder returns 400, and another center's log id returns 404.
