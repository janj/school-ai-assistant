# Track E: Q/A logging, PII scrubbing, log viewer

**Branch:** `track/e-qa-logging` · **Port:** 8105 · **Owns:** `app/qa_log.py`, `app/routes/admin_logs.py`, `static/admin/logs.js`, `static/admin/logs.css` (new, imported by logs.js), `docs/features/qa-logging.md`

## Goal
Every question and answer is logged **with PII removed**, so the team can check and improve
answers. Admins see their own center's logs. IPs are never stored anywhere.

## `app/qa_log.py`
- Implement `log_turn(...)` exactly as the stub's signature (CONTRACTS §5). Track B calls it.
- It must **return immediately and never raise**. Hand the work to a background
  `ThreadPoolExecutor(max_workers=2)` and catch and log every exception there.
- **Scrub, in two passes:**
  1. Regex, always: emails → `[email]`, phone numbers (US formats, with or without
     parentheses, dashes, dots or spaces) → `[phone]`, street addresses → `[address]` (best
     effort), and long digit runs (SSN, card or account numbers, 6+ digits) → `[number]`.
  2. A Haiku pass (`config.FAST_MODEL`) to replace **people's names** (children and parents)
     with `[name]`. Also replace other personal details: dates of birth, medical details about
     a specific child.
     - **Keep** staff names that appear in the center's directory (`contacts.name` for that
       center): they're public info and useful for checking answers. Pass that list to Haiku
       as names to keep.
     - Use structured output (`output_config.format` with a JSON schema `{text: string}`) and
       a short system prompt.
     - If Haiku fails, store the regex-only result and set nothing else. Never store raw text.
     - Note: Haiku 4.5 doesn't take `effort`. Don't send it.
- Scrub the question, the answer and `rewritten_query` (if given). Then insert one `qa_log` row
  with the usage fields, latency, `found`, `sources_json`, and the session's `role`. Don't store
  any IP.
- Also expose `scrub_regex(text)` and `scrub(text, keep_names)` as plain functions so other
  code can reuse them.

## `app/routes/admin_logs.py` (API in CONTRACTS §3)
- Every route depends on `session.require_admin` and filters `WHERE center_slug = ?` using the
  session's center.
- `GET /api/admin/logs?found=all|false|true&limit=50&offset=0`: newest first. Return
  `sources` as a parsed list.
- `GET /api/admin/logs/stats`:
  `{total, unanswered, last_7_days, tokens: {input, output, cache_read}}`.

## `static/admin/logs.js`: export `mount(el, session)`
- A stats strip at the top: total questions, unanswered, last 7 days, cache-read share.
- A filter: All / Unanswered / Answered.
- Each entry is a card: time, role, scrubbed question, answer (collapsed after 3 lines and
  expandable), source chips, a "not found" badge, and tokens and latency in muted text.
- "Load more" for paging. Works on mobile at 360px wide. Use the `base.css` tokens.
- Leave a hook for Track H (unanswered → FAQ): a clearly marked spot on each unanswered card,
  `// HOOK(faq): "Answer this" action mounts here`.

## Check
B may not be merged yet, so call `log_turn` directly from a small throwaway script (not
committed). Feed it text containing a made-up child's name, a parent phone number and an email.
Then check the stored row in `sqlite3` and in the Logs tab as an admin. Confirm a parent session
gets 403, and that center A's admin can't see center B's rows.
