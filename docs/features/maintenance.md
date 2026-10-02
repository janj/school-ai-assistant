# Knowledge maintenance agent (Track K)

Spec: `docs/KNOWLEDGE_MAINTENANCE.md` §3. This page records how it is built.

## What it does
`app.maintenance.run(slug, rules=True, ai=False, dry_run=False)` checks one center and returns a
summary (checks run, auto-fixes, issues opened/resolved, AI token usage).

- **Rule checks (free):** lint findings (`app/lint.py`, moved from `scripts/kb_lint.py`, unchanged),
  closures running out within 60 days, missing required policy topics, contacts with no phone or
  email, `facts` rows no policy/FAQ uses.
- **Auto-fix:** only lint `duplicate` findings (an identifier or amount with one keyed home).
  All of these must hold, or it stays an issue:
  1. the replacement is made in prose only, never inside an existing `{{...}}`;
  2. the field renders to the same text before and after;
  3. it passes the admin editor's own `_validate` and `_check_placeholders`;
  4. after writing, `kb.render_center_kb` is byte-identical to before (otherwise the edit is
     reverted and logged as an error);
  5. an `audit_log` row is written with `admin_name='kb-maintenance-agent'` and before/after.
  Effect: `$75.00` becomes `{{fee:registration}}`, but a typed `$75` does not (it would render as
  `$75.00`), and a person's name does not (the placeholder adds the title, "..., RN"). Both go to review.
- **AI check (`--rules-only` skips it):** `config.ANSWER_MODEL`, `effort: "low"`, JSON-schema output.
  System blocks are cached like `chat.py` (instructions, then the center KB). It also gets the last
  30 days of unanswered `qa_log` questions (grouped, max 40, marked untrusted). Output
  (`conflict | reworded_duplicate | gap`) is never applied, only queued.

## Queue (`kb_issues`)
`UNIQUE(center_slug, fingerprint)` prevents duplicates. A re-run updates an open issue, reopens a
resolved one that reappears, leaves a dismissed one alone, and resolves an open one that no longer
reproduces (`resolved_by='kb-maintenance-agent'`). A rules-only run only resolves rule kinds; AI kinds
are only resolved by an AI run. AI wording varies between runs, so its fingerprint is
kind + section (+ ordinal when one section has several).

## Surfaces
- `scripts/maintain_kb.py --all | <slug>... [--rules-only] [--dry-run] [--json]`.
- API (admin only, own center): `GET /api/admin/issues?status=`, `POST /api/admin/issues/{id}/status`,
  `POST /api/admin/issues/run {ai}` (AI limited to once per 10 minutes per center, in memory, 429
  with a friendly message; a failed AI call does not use up the allowance), and
  `GET /api/admin/issues/auto-fixes` (the agent's `audit_log` rows, for the tab).
- "Data issues" tab: open issues with severity, section, detail, suggestion; resolve/dismiss;
  "Run check now" with an "include AI review" box; recent automatic fixes.

## Decisions
- The write path reuses `app/routes/admin.py` helpers (private names) rather than copying them, so a
  rule change in the editor applies to the agent too.
- Added `auto-fixes` as a fourth route; the brief's three routes can't list the agent's edits cheaply.
- Schedule is documented in `KNOWLEDGE_MAINTENANCE.md` only. Nothing installs cron.
- Cost seen on the seeds: about 8.5k cached input tokens plus about 1.2-1.7k output per center per AI run.
