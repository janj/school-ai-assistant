# Track A: Seed data

**Branch:** `track/a-seed-data` · **Port:** 8101 · **Owns:** `seed/` (except `seed/_example/`), `docs/features/seed-data.md`

## Goal
Write two made-up childcare centers with realistic, detailed data that is **clearly different
between the two**. Then the chat can show that it keeps centers separate. For example, if both
centers have the same late fee, a mix-up between them wouldn't show.

For inspiration on structure and tone, look at the City of Albuquerque Division of Child and
Family Development family handbook (2019):
https://www.cabq.gov/family/documents/2019-division-of-child-and-family-development-family-handbook-final.pdf
**Do not copy its data, names, numbers or wording.** Everything must be made up.

## The two centers
1. **`juniper-hill`**: "Juniper Hill Early Learning Center". A larger public-style program for
   infants through pre-K. Earthy green theme. Hours 6:30–18:00. Stricter policies. Monthly
   tuition that depends on age group.
2. **`little-comets`**: "Little Comets Preschool". A small private preschool for ages 2–5.
   Navy/yellow space theme. Hours 7:30–17:30. Part-day and full-day options. Weekly tuition.
   Different lunch arrangement (e.g. families pack lunch, the center provides snacks).

## Content to cover (each center)
Follow the shapes in `docs/CONTRACTS.md` §7 exactly. `db.load_seed` inserts the JSON keys
straight in as column names, so the keys must match.

- **Directory:** 6–10 contacts (director, assistant director, front desk, enrollment
  coordinator, nurse/health, food service, lead teachers), each with a position and a phone
  and/or email.
- **Hours:** weekdays, weekends, plus any early-release notes.
- **Closures:** 2026-08 through 2027-07. Holidays, staff training days, winter break.
- **Daily schedule:** per age group, from arrival to departure, including meals and nap.
- **Fees:** tuition per age group/option, registration, supply fee, late-pickup fee (per minute
  or per block), returned payment, sibling discount (shown as a note or as a negative amount).
- **Lunch:** at least a one-week menu (breakfast, lunch, PM snack), or packed-lunch rules for
  Little Comets.
- **Policies** (`policies/<topic>.md`, starting with a `# Title` line):
  - Required: `late_pickup`, `arrival_dropoff` (including late arrival), `items_from_home`
    (allowed and not allowed), `enrollment` (steps, documents, immunizations, waitlist),
    `birthdays` (treats, no-food alternatives), `illness_exclusion` (fever thresholds,
    symptoms, how long to stay home, return rules), `lunch_info` (allergies, outside food).
  - Optional: `payments`, `general`.
- **Theme** in `center.json`: `primary`, `accent`, `background`, `font` (a system font stack),
  `logo_text` (2–3 letters).

**Leave some gaps on purpose** so the "not found" path gets exercised: e.g. no field-trip
policy, no summer camp info, no transportation/bus service.

Phone numbers use `(505) 555-01xx`. Email domains end in `.test`.

## `eval_questions.md` (each center)
- ~20 questions with the expected answer and the section it comes from.
- ~5 questions the data **cannot** answer, with the expected behavior: say it's not known and
  give the main phone/email.
- 3 follow-up pairs (a question, then a follow-up that depends on it, e.g. "What's the late
  fee?" → "And after 6:15?").
- 2 questions in Spanish.

## Check
Delete `data/school.db` and start the app. Then:
- `GET /api/centers` lists both centers.
- Spot-check rows with `sqlite3 data/school.db`.
- `seed/_example` must no longer load (it is skipped automatically once real seeds exist).
