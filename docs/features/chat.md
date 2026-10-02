# Chat backend (Track B)

`POST /api/chat` calls `chat.answer()`. Answers come only from the session's center's data.

## Flow
1. `limits.check(ip)` rejects with 429 (`rate` or `budget`) before any model call.
2. `kb.render_center_kb(slug)` reads that center's rows and renders text. Every section starts
   with `[section: <id>]` (IDs in CONTRACTS §4). Money is `$1,234.00`, times `7:00 AM`, dates
   `Thursday November 26, 2026`; the schedule is grouped by age group; policy markdown is kept.
3. One call to `client.beta.messages.create` (model `config.ANSWER_MODEL`):
   - `system` = [RULES (cached), KB text (cached)]; the user message holds today's date and the
     question, so the date never breaks the cache.
   - `output_config` = `{effort: "low", format: json_schema{answer, found, sources}}`.
   - Beta `server-side-fallback-2026-07-01` with `fallbacks="default"`.
4. Parse the JSON, then ground it server-side: drop `sources` that aren't real section IDs for
   this center; `found=true` with no valid source becomes `found=false` (warning logged). When
   `found=false` the server attaches `{phone, email}` from the `centers` row, never the model.
5. Record tokens in `limits`, then `qa_log.log_turn(...)`.

## Decisions
- **No KB cache; re-render per request.** A few small SQLite queries, and admin edits (Track D)
  are visible immediately. Output is deterministic, so the prompt cache only changes with data.
- **Refusal** (`stop_reason == "refusal"`) or unparseable output returns `found=false` with a
  polite message and the center contact.
- **Errors:** connection, rate-limit and 5xx errors raise `UpstreamError` (route returns 503);
  other 4xx errors propagate as bugs. A missing API key is an `UpstreamError` with a log line.
- **Rate limit** counts a request at `check` time so concurrent bursts can't slip past it.
  Budgets use sliding windows: tokens in the short window (`TOKEN_BUDGET_SHORT` over
  `TOKEN_BUDGET_SHORT_WINDOW_S`) and in the last 24h (`TOKEN_BUDGET_DAILY`, a rolling day, not
  calendar day). Tokens recorded = input + output + cache-write + 10% of cache-read.
  State is in memory only, pruned on each check; an IP with no recent activity is dropped.
- `qa_log` receives `response.model`, which can differ from `ANSWER_MODEL` if the fallback fired.
- **Partial answers (Phase 2).** `found=true` only when the knowledge base directly answers the
  question. If the model can only offer related facts, `found` stays false (so the contact card
  shows) but its `sources` are kept, so the related facts are still cited.
- `conversation_id` is echoed back and otherwise ignored.

## Observed
With the real seed data (Phase 2, all 62 eval questions), the cached prefix is ~8,200 tokens for
Juniper Hill and ~7,200 for Little Comets; repeat questions send ~35 uncached input tokens and
read the rest from cache. Limits were tunable via
`RATE_LIMIT_REQUESTS`, `TOKEN_BUDGET_SHORT`, `TOKEN_BUDGET_DAILY`.
