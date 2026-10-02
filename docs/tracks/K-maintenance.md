# Track K: Knowledge maintenance agent

**Branch:** `track/k-maintenance` · **Port:** 8115 · **Owns:** `app/maintenance.py` (new), `app/lint.py` (new; the logic moved out of `scripts/kb_lint.py`), `scripts/kb_lint.py` (becomes a thin wrapper), `scripts/maintain_kb.py` (new), `app/routes/admin_issues.py` (new), `static/admin/issues.js` + `issues.css` (new), `docs/features/maintenance.md`. **Allowed exceptions:** add the `kb_issues` table to `app/schema.sql`; add one `include_router` line to `app/main.py`; add a "Data issues" tab button and module entry to `static/admin.html`.

## Goal
Implement the agent specified in **`docs/KNOWLEDGE_MAINTENANCE.md` §3**. Read it closely:
it's the spec. The schedule (cron) is **documented only, not installed**. Build the script, the
admin queue and the on-demand run.

## Pieces
1. **`app/lint.py`:** move `lint_center()` and its helpers from `scripts/kb_lint.py` without
   changing behavior. `scripts/kb_lint.py` imports it and keeps its CLI and exit codes.
2. **`kb_issues` table:**
   `id, center_slug, kind, severity (high|medium|low), section, detail, suggestion,
   fingerprint, status (open|resolved|dismissed), created_at, updated_at, resolved_by`.
   - `UNIQUE(center_slug, fingerprint)` so re-runs don't duplicate issues.
   - An issue that no longer reproduces on a re-run is set to `resolved` with
     `resolved_by='kb-maintenance-agent'`.
3. **`app/maintenance.py`: `run(center_slug, *, rules=True, ai=False, dry_run=False) -> summary`.**
   - **Rule-based checks** (KNOWLEDGE_MAINTENANCE §3 table):
     - lint findings;
     - closure calendar coverage under 60 days ahead;
     - missing required policy topics (CONTRACTS §7);
     - contacts with neither phone nor email;
     - unused `facts` rows.
   - **Auto-fix**, exactly per §3. Only `duplicate` findings (an identifier or amount with a
     single candidate) qualify. Apply one only if:
     - the center's **filled-in KB text is byte-for-byte identical** before and after
       (`kb.render_center_kb`);
     - it goes through the same validation as an admin save;
     - it's recorded in `audit_log` with `admin_name='kb-maintenance-agent'` and before/after
       values.

     Everything else becomes an issue.
   - **AI check** (`config.ANSWER_MODEL`, Sonnet 5.5):
     - The center KB goes in a cached system block, the same layout as `chat.py`.
     - It returns structured output: a list of
       `{kind: conflict|reworded_duplicate|gap, section, detail, suggestion}`.
     - It also sees a summary of the last 30 days of unanswered `qa_log` questions, for gaps.
     - Use `effort: "low"`. Never send `thinking: {"type": "disabled"}` (400 on Sonnet 5.5).
     - **Never auto-apply** its output: issues only.
4. **`scripts/maintain_kb.py`:** `--all | <slug>...`, `--rules-only`, `--dry-run`, `--json`.
   Prints a summary per center (checks run, auto-fixes, issues opened/resolved).
5. **Admin API (`app/routes/admin_issues.py`).** All routes are admin-only and use the
   session's center.
   - `GET /api/admin/issues?status=open`
   - `POST /api/admin/issues/{id}/status` with `{status: resolved|dismissed}`
   - `POST /api/admin/issues/run` with `{ai: bool}`. Limit it to once per 10 minutes per
     center for `ai=true`, with 429 and a friendly message. Return the summary.
6. **"Data issues" tab (`static/admin/issues.js`, `export function mount(el, session)`).**
   - An open-issues list with a severity badge, section, detail and suggestion.
   - Resolve and dismiss actions.
   - A "Run check now" button, with an "include AI review" checkbox.
   - A "Recent automatic fixes" list from `audit_log` where `admin_name='kb-maintenance-agent'`.
   - Mobile and desktop layouts.

## Check
- On the current seed: lint has 0 failing findings, so expect few or no rule issues. The
  "24 hours" item is `possible_duplicate`, so it is review only.
- To exercise auto-fix, plant literals in a **local** database only (never in seed):
  - a phone number that matches one contact;
  - "$75" in a policy (single candidate);
  - "(505) 555-0120" (ambiguous: front desk and center main phone);
  - "3:30 PM" (a time: must not be auto-fixed).

  Show which got auto-fixed, and that the filled-in KB was unchanged for each.
- Run the AI check once per center and report the issues and their cost (tokens).
- Confirm another center's issue ids return 404 and parents get 403.
