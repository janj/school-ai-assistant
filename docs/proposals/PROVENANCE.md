# Proposal: provenance for all knowledge-base data

**Status:** proposed, not started · **Priority:** higher than the [center import agent](CENTER_IMPORT_AGENT.md),
which depends on it · **Written:** 2026-10-01

## Why

Today we can say *who changed* a value (`audit_log`) but not *why we believe it is true*. When
the assistant tells a parent "the late fee is $2.00 per minute", nothing records where that came
from (the handbook? a director's email? a guess during setup?) or when it was last confirmed.

That's the weak link in the "nothing made up" promise. The model can't invent values, but the
**data** can still be wrong, out of date or of unknown origin, and there's no way to tell which.
Provenance makes every fact traceable to a source and a date. That enables:

- **Trust and review:** an admin (or a parent, if we choose) can see where an answer came from.
- **Freshness:** facts not confirmed in N months can be flagged before they go stale.
- **Safe automation:** the import agent and the maintenance agent can only write values they can
  source, and the evidence is kept.
- **Accountability:** for a regulated setting like childcare, "where did the assistant get that?"
  should always have an answer.

## Concepts

- **Source:** something a fact can come from: a document (handbook PDF, web page), a person
  (an admin attesting to it), the seed data, an admin's FAQ answer to a logged question, or an
  agent's verified fix.
- **Provenance record:** links one stored value (a table row, optionally one field) to a source,
  with the supporting quote where there is one, when it was recorded and when it was last verified.
- **`audit_log` vs provenance:** `audit_log` answers *what changed and who changed it*.
  Provenance answers *why we believe the current value*. Every write records both.

## Proposed schema

```sql
CREATE TABLE sources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug   TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('document', 'web', 'admin', 'seed', 'faq', 'agent')),
    ref           TEXT,          -- URL, seed file path, qa_log id, admin name...
    title         TEXT,          -- "2026-27 Family Handbook", "Director (verbal)"
    published_at  TEXT,          -- the document's own date, if known
    retrieved_at  TEXT,          -- when we fetched or recorded it
    content_hash  TEXT,          -- for documents: detect when the source itself changes
    UNIQUE (center_slug, kind, ref)
);

CREATE TABLE provenance (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug  TEXT NOT NULL,
    table_name   TEXT NOT NULL,   -- contacts, fees, policies, facts, ...
    row_id       INTEGER NOT NULL,
    field        TEXT,            -- NULL = the whole row
    source_id    INTEGER NOT NULL REFERENCES sources(id),
    quote        TEXT,            -- verbatim supporting text (documents, web)
    locator      TEXT,            -- "p. 12", "#fees", heading path
    recorded_by  TEXT NOT NULL,   -- admin name or agent id
    recorded_at  TEXT NOT NULL DEFAULT (datetime('now')),
    verified_at  TEXT NOT NULL DEFAULT (datetime('now')),  -- last time someone or something re-confirmed it
    superseded   INTEGER NOT NULL DEFAULT 0                -- 1 once the value changes
);
CREATE INDEX provenance_row ON provenance (center_slug, table_name, row_id);
```

Civic Mined's `budget_data_sources` (`src/parsers/provenance.py`) solves a similar problem:
documents are registered first, then each ingest batch links rows to a document and page range.
This proposal applies the same idea at field level, and adds people as sources.

## How each write path records provenance

| Write path | Source | Notes |
|---|---|---|
| Seed load | `seed`, ref = `seed/<slug>/<file>` | Backfill for existing rows. Our seed data is fictional, so these are clearly marked "sample data" |
| Admin edit (Data tab) | `admin` (attested) by default. The edit form gets an optional **"Source"** field (pick a known document, paste a URL, or "verbally confirmed by…") and an optional quote | The previous provenance for that row/field is marked `superseded` |
| Admin FAQ answer (Logs tab) | `faq`, ref = the qa_log id, plus the admin's attestation | |
| Maintenance auto-fix | Unchanged: placeholder conversions don't change a value, so the existing provenance stays | Agent fixes that *change* a value aren't allowed today, and would need a source |
| Import agent | `web` / `document`, with quote and locator, **after** the non-AI check that the quote is in the fetched text | See the import proposal |
| Reset to seed | Supersedes everything for the center and reloads seed provenance | |

**Placeholders:** policy text that uses `{{fee:registration}}` takes its provenance for that value
from the fee row. The policy's own provenance covers its prose only.

## Using provenance

1. **Admin view:** each row in the Data tab shows a source badge (Handbook p.12 · verified Aug
   2026). Expanding it shows the quote and the change history. Rows with only `seed` or
   unsourced provenance stand out.
2. **Freshness checks (maintenance agent):** a new rule-based check flags facts whose
   `verified_at` is older than a threshold (e.g. fees 12 months, closures once the calendar year
   rolls over, contacts 6 months), and sources whose `content_hash` changed since retrieval
   ("the handbook was updated; 14 facts came from it"). A "Re-verify" action updates
   `verified_at` after a person confirms.
3. **Answers:** `ChatAnswer.sources` already lists the section IDs used. Provenance lets the UI
   turn "Fees" into "Fees · Family Handbook 2026-27". Whether parents see source names is a
   product choice. Admins should always see them in the Logs tab.
4. **The KB prompt stays deterministic:** provenance is **not** put into the cached knowledge
   base text by default. That keeps prompt caching intact and avoids the model narrating
   sources. If we later want the model to say "according to the handbook", add short source
   labels per section. They change only when sources change, so caching survives.

## Rules (proposed)
- Every content row has at least one non-superseded provenance record. The lint gets a check:
  "unsourced row".
- Imported or agent-written values must carry a quote that has been checked in code.
- Provenance is append-only: change it by superseding, never by editing or deleting. That gives
  a full history next to `audit_log`.
- Center isolation: provenance and sources are filtered by `center_slug`, like everything else.

## Effort
Medium: one serial contracts step plus two parallel tracks.
- **Contracts (operator + Opus):** schema and migration, a seed backfill, a
  `provenance.record(...)` helper used by every write path, and CONTRACTS updates (the admin
  write body gains an optional `source`).
- **Track 1:** admin UI (source field on edit, badges, a provenance panel, Re-verify).
- **Track 2:** maintenance checks (unsourced rows, stale `verified_at`, changed source documents)
  and source names in the Logs tab.

## Open questions
- Should parents see source names in answers, or only admins?
- Freshness thresholds per table: who sets them, and are they per center?
- Do we store copies of source documents (needed to re-check quotes later), or only hashes and
  URLs?
