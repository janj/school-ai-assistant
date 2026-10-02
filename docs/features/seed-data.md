# Seed data (Track A)

Two made-up centers, loaded on first start by `db.init_db()`. Everything is invented; phone numbers are `(505) 555-01xx` and emails end in `.test`.

## Files
`seed/<slug>/` holds `center.json`, `contacts.json`, `hours.json`, `closures.json`, `schedule.json`, `fees.json`, `lunch.json`, `policies/*.md` and `eval_questions.md` (the last is a manual checklist, not loaded). Shapes follow `docs/CONTRACTS.md` section 7. Both are generated to match the table columns, so `db.load_seed` is a plain loader.

## How the centers differ (so mix-ups show)
| | Juniper Hill (`juniper-hill`) | Little Comets (`little-comets`) |
|---|---|---|
| Size and ages | Large, 6 weeks to 5 years | Small, ages 2 to 5 |
| Hours | 6:30 AM-6:00 PM, last-Friday 3 PM release | 7:30 AM-5:30 PM, Wednesday 3:30 PM release |
| Tuition | Monthly by age ($920-$1,420) | Weekly by part/full-day and 3/5 days ($110-$285) |
| Late pickup | $2 per minute from 6:01, no grace | $15 per 15-minute block after 10 minutes' grace |
| Fever | 100.4 F; 24 hours fever-free | 100.0 F; 24 hours fever-free, 48 hours after vomiting |
| Meals | Kitchen provides breakfast, lunch and snack | Families pack lunch; center gives AM snack |
| Sibling discount | 10% of older child's tuition | $10 per week per extra child |
| Registration | $75 | $50 |
| Closures | Public-holiday calendar, open in summer | Spring break, closes for summer after 2027-06-04 |
| Theme | Green/gold, serif | Navy/yellow, sans |

## Deliberate gaps
Neither center has field-trip, transportation, or summer-camp information (Little Comets only says it closes after the last day). The `eval_questions.md` files list these as the "not found" cases, plus a cross-center question for each.

## Notes
- Sibling discounts: Juniper Hill is a note (percentage); Little Comets uses a negative `amount_cents`.
- The Little Comets director appears twice in the directory (director and health officer) because a small staff shares roles.
