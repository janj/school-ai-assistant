# Q/A logging and log viewer (Track E)

Every answered question is logged with PII removed, so the team can check answers and find gaps.
Admins see only their own center's log. No IP is ever stored.

## How it works

- **`qa_log.log_turn(...)`** (called by Track B) queues the work on a `ThreadPoolExecutor(2)` and
  returns at once. It never raises; failures are logged by the worker and the turn is dropped
  rather than stored raw.
- **Scrub, two passes** (`scrub_regex`, `scrub`, both reusable):
  1. Regex: emails -> `[email]`, US phones -> `[phone]`, street addresses -> `[address]`
     (best effort: number + up to 4 words + street suffix, optional apt/unit), digit runs of 6+ ->
     `[number]`.
  2. Haiku (`config.FAST_MODEL`, structured output `{text}` via `output_config.format`, no
     `effort`) replaces people's names with `[name]`, dates of birth with `[dob]` and medical
     details about a child with `[medical]`. Staff names from the center's `contacts` table are
     passed as a keep-list.
- Question, answer and `rewritten_query` are scrubbed separately, then one `qa_log` row is
  inserted with usage, latency, `found`, `sources_json` and the session's `role`.
- **API** (`app/routes/admin_logs.py`): `GET /api/admin/logs` and `/stats`, both behind
  `require_admin`, both filtered by the session's `center_slug`.
- **UI** (`static/admin/logs.js` + `logs.css`): stats strip, All/Unanswered/Answered filter, cards
  (3-line clamp with expand, source chips, "not found" badge, tokens/latency), "Load more".
  Text is rendered with `textContent`, never as HTML.

## Decisions

- **Fail closed on raw text, fail open on Haiku.** If Haiku errors or no API key is set, the
  regex-only text is stored (never the raw text). Names may then remain in that row.
- Regex runs first, so Haiku never sees emails, phones or numbers.
- The center's own phone in an answer is also replaced by `[phone]`; regex can't tell it apart
  from a parent's. Acceptable for a POC.
- Haiku is called once per text field (up to 3 calls per turn), keeping the schema to `{text}`.
- Cache-read share in the UI = `cache_read / (input + cache_read)`.
- The Unanswered card has a marked empty `div.faq-hook` for Track H.

## Try it

Call `log_turn` from a script, then `sqlite3 data/school.db "select question, answer from qa_log"`,
or sign in as admin and open the Logs tab. A parent session gets 403 on both routes.
