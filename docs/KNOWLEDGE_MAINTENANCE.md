# Knowledge maintenance

The assistant is only as correct as each center's knowledge base. Duplicated, stale or
conflicting facts are the main way it goes wrong *without* making anything up: it faithfully
repeats bad data, or reports a conflict instead of answering. This document defines how the
knowledge base must be written (§2) and how it is kept healthy over time (§3).

## 1. Why this is needed

In Phase 2 we found **18–22 facts per center** repeated in policy prose that also live in the
structured tables: fees, contact phones/emails and times. When an admin changed the registration
fee in `fees`, the enrollment policy still said $75. The assistant noticed both values and
reported a conflict, which is the correct behavior but still a failed answer.

Every center will drift like this as staff edit the data over months. So it needs **authoring
rules that prevent drift** and **a recurring check that catches what gets through**.

## 2. Authoring rules (Phase 3.0)

1. **Every fact has exactly one home.**
   - Fees go in `fees`, people in `contacts`, opening times in `hours`.
   - Reused facts that have no table (fever threshold, grace period, …) go in `facts`.
   - Policies hold the *rules and explanations*, not copies of values.
2. **If prose needs a value, use a placeholder:** "A {{fee:registration}} registration fee is
   due when a place is accepted." The server fills it in. Parents and the model see
   "$75.00".
3. **If prose doesn't need the value, point to its home:** "Late fees are listed under Fees",
   or "call the nurse (see Directory)".
4. **Never type a value that has a home.** A literal "$75" or "(505) 555-0124" in a policy is a
   bug, even if it's correct today.
5. **Keys are stable.** A key (`registration`, `nurse`, `fever_threshold`) is chosen once when
   the row is created and never renamed. Deleting a row that a policy uses is blocked.
   - *POC assumption:* the code enforces uniqueness, immutability and in-use checks.
     Deleting a row and re-adding it under a new key is not prevented.
   - *Production:* key pickers, a shared key vocabulary across centers, and rename migrations.

Placeholder reference: `{{fee:key}}`, `{{contact:key.phone}}`, `{{hours:key.close}}`,
`{{fact:key}}`, `{{center:main_phone}}`. The full grammar is in `CONTRACTS.md` after Phase 3.0.

## 3. Maintenance agent (Track K)

An agent checks each center's knowledge base on a schedule, **fixes issues itself only when the
fix is clear-cut and provably safe**, and puts everything else in a review queue for the center's
admins.

### What it checks

**Rule-based checks (free, every run):**

| Check | Example | Action |
|---|---|---|
| Typed literal that matches exactly **one** keyed value | "$75" in enrollment, and only `fee:registration` is $75 | **Auto-fix**: replace with `{{fee:registration}}` |
| Typed literal that matches **several** keyed values | "$15": late fee and returned-payment fee | Flag, listing both candidates |
| Broken placeholder (e.g. after a reset or bad import) | `{{contact:cook}}` with no such key | Flag |
| Closure calendar running out | No closures dated after the next 60 days | Flag: "add next year's closures" |
| Missing required policy topic | No `illness_exclusion` policy | Flag |
| Contact unreachable | Directory row with neither phone nor email | Flag |
| Unused `facts` row | Never used, and not useful on its own | Flag (low) |

**AI checks (Claude Sonnet, weekly or after N edits, center knowledge base cached):**

| Check | Example | Action |
|---|---|---|
| Conflicts between sections | Policy says pickup by 5:30, hours say 6:00 | Flag, with a suggested fix |
| Reworded duplicates | "seventy-five dollars", "half an hour after closing" | Flag, with the suggested placeholder |
| Gaps shown by real questions | Cluster of unanswered questions about field trips | Flag: suggest an FAQ or policy (links to Track H's queue) |

### When it may fix things itself

An auto-fix is applied only if **all** of these hold:
1. **Rule-based:** the fix comes from code, not from a model's judgment.
2. **Meaning unchanged:** the center's filled-in knowledge base text is **byte-for-byte identical**
   before and after. Replacing "$75.00" with `{{fee:registration}}` passes. Anything that changes
   what the model sees fails, and goes to the queue instead.
3. **Reversible and attributed:** the fix goes through the normal admin write path and is recorded
   in `audit_log` as `admin_name = "kb-maintenance-agent"` with before/after values, so an admin
   can see and revert it.

Model-suggested changes are **never** applied automatically. They become queue items with the
suggestion attached, and an admin accepts, edits or dismisses them.

### Outputs
- A `kb_issues` table: `center_slug, kind, severity, section, detail, suggestion, status
  (open/resolved/dismissed), created_at, resolved_by`. Issues are de-duplicated by
  (center, kind, section, detail), so re-runs don't pile up copies.
- A **"Data issues"** admin tab next to Logs: a count of open issues, accept/dismiss controls, and
  a list of recent auto-fixes with links to History.
- A run summary in the app log: checks run, auto-fixes applied, and issues opened or closed.

### Running it
- **Scheduling is documented, not installed (POC decision).** The intended schedule is
  **nightly** rule-based checks and **weekly** AI checks. To turn it on, add this to root's
  crontab on the droplet (`crontab -e`):
  ```
  # nightly rule-based checks, 03:15 UTC
  15 3 * * *  cd /opt/school-ai && docker compose -f deploy/docker-compose.yml exec -T app python scripts/maintain_kb.py --all --rules-only >> /var/log/kb-maintenance.log 2>&1
  # weekly rule-based + AI checks, Sundays 04:00 UTC
  0 4 * * 0   cd /opt/school-ai && docker compose -f deploy/docker-compose.yml exec -T app python scripts/maintain_kb.py --all >> /var/log/kb-maintenance.log 2>&1
  ```
  Nothing in `deploy/` installs this, so it stays an explicit operator decision.
- **On demand**: a "Run check now" button in the Data issues tab, limited to the admin's own center.
- `--dry-run` prints what it would fix or flag without writing anything.
- **Cost:** the rule-based checks are free. The AI check is about 8k cached tokens per center per
  run, a few cents a month at POC scale.

### Who owns what
Center admins own their queue. The agent owns nothing: every change it makes is an ordinary,
attributed, reversible edit. If it ever applies a bad fix, that's a bug in the "meaning
unchanged" check (rule 2) and must be fixed there, not patched around.
