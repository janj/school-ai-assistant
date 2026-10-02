# Proposal: center import agent (URL → seed data)

**Status:** for future consideration, not started · **Depends on:** [provenance](PROVENANCE.md)
· **Written:** 2026-10-01

## Goal

Given a center's or school's website URL, produce a **draft** center: directory, hours, closures,
schedule, fees, lunch, facts and policies, in our seed schema. Every value carries evidence from
the site. An admin reviews and publishes it. Gaps become review items, not guesses.

## Why it fits this codebase

Most of the hard parts already exist:
- **Target schema:** the seed format (CONTRACTS §7) and `db.load_seed`-style loading.
- **One home per fact:** keys, the `facts` table and placeholders (Phase 3.0). Extracted policy
  text can be normalized with Track K's safe auto-fix: typed values become placeholders.
- **Quality checks:** `kb_lint`, the maintenance agent's rule-based and AI checks, and
  `run_evals.py`.
- **Review queue:** Data issues, for gaps and conflicts.

What's new: fetching, extraction with evidence, a draft/publish lifecycle, and provenance
(which should be built first).

## Pipeline

```
URL → fetch (pages + linked PDFs such as a family handbook)
    → extract per table, with structured output; every value comes with {url, quote, locator}
    → check evidence in code (the quote is in the fetched text; the value is in the quote)
    → normalize (role-based keys, typed values → placeholders, required-topic check)
    → validate (lint, AI consistency check) → DRAFT center (hidden from the picker)
    → admin review (each row next to its source) → publish
```

## Design decisions

1. **"Nothing made up" applies to ingestion too.** Every extracted value must cite a source URL
   and a verbatim quote. A non-AI check confirms that the quote appears in the fetched text (after
   whitespace normalization) and that the value appears in the quote. Values that fail are
   dropped and become issues; they're never quietly kept. The model extracts; code verifies.
2. **Gaps are expected.** Most sites don't publish fees, a full closure calendar or an illness
   policy. Missing required topics become Data issues ("No illness policy found on the site").
   The assistant's existing "not found → contact the center" behavior covers the rest.
3. **Draft before live.** `centers.status` (`draft | published`); drafts are hidden from
   `/api/centers`. Imports go into the database with provenance. An optional "export to seed"
   writes `seed/<slug>/` if a center should be tracked in the repo.
4. **Our own fetcher; the model only extracts.** `requests` + BeautifulSoup + `pdfplumber`
   (the same stack as Civic Mined). This keeps evidence checks, caching, PDF handling and crawl
   limits under our control. Claude's built-in web fetch tool is a possible simplification, but
   it's harder to verify and cache.
   - **Crawl limits:** respect robots.txt, stay on the same domain, a max page count and size,
     timeouts, and a polite delay.
   - **Exposed in a UI:** block private and loopback addresses (SSRF protection), and require an
     operator passcode. Anyone can pick Admin today, so an open "import any URL" button would
     let anyone spend our API budget.
5. **Reuse the post-processing:**
   - keys come from roles and are checked with `placeholders.KEY_RE`;
   - Track K's safe auto-fix converts identifiers and amounts into placeholders;
   - the AI consistency check runs on the draft before an admin sees it;
   - the theme comes from the site's `theme-color` meta tag and dominant CSS colors, run
     through `theme.js`'s contrast check (ported to Python).
6. **Command line first:** `scripts/import_center.py <url> [--slug] [--max-pages]`. An admin UI
   button can come later, behind the operator passcode.
7. **Real centers:** importing a real center's site produces an assistant that speaks for it.
   Real-site imports stay **private drafts, labeled unofficial**, unless the center has agreed.

## How we'd know it works
- **Round-trip test with known answers:** render our two fictional centers into a static test
  site (HTML pages plus a PDF handbook built from the seed), import it, and diff the result
  against the seed. That gives precision and recall per table and per field.
- **Real sites:** 2–3 public center sites, including the City of Albuquerque family handbook PDF
  referenced in the original brief, imported as private drafts. Real sites test messy layouts
  and gaps.
- **Starter test questions:** the importer writes an `eval_questions.md` from what it extracted,
  plus "not answerable" questions for each gap, so `scripts/run_evals.py` works on an imported
  center immediately.

## Cost
A typical site is about 20–50 pages plus a handbook, roughly 100–300k input tokens. Extraction
with Sonnet 5.5 (`effort: medium`, structured output) costs well under **$1 per center**. It isn't
latency-sensitive, so the Batch API halves that.

## Effort
About the size of Phase 1:
- **Phase 4.0 (operator + Opus):** contracts. Draft status, the extraction output schema (the
  seed format plus `{url, quote, locator}` per value), fetcher safety rules, and the
  import-job record. Requires provenance to be in place.
- **Parallel tracks:**
  1. **Fetcher:** crawl, PDF text, caching, limits.
  2. **Extraction:** per-table prompts with structured output, plus the evidence check in code.
  3. **Normalization and validation:** keys, placeholders, required topics → issues, theme.
  4. **Review UI:** draft list, row-by-row review with sources, publish.
  5. **Test harness:** the round-trip test site, an importer test script, and a real-site runbook.
- **Integration:** round-trip results, 2–3 real sites, docs.

## Open questions
- Re-import: when a site changes, update an existing center (diffs go to review) or only create
  new ones?
- How much of a handbook PDF should become policies verbatim, versus summarized? Verbatim is
  easier to verify; summaries read better.
- Who can trigger imports in a shared deployment?
