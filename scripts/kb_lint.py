"""Knowledge-base lint: values typed into prose that already have a home, and broken placeholders.

Deterministic, no model calls. The logic lives in app/lint.py. Reads the live database (default: data/school.db).
Exit code 1 if anything is found, so it can gate a deploy or feed Track K's maintenance agent.

    uv run python scripts/kb_lint.py                 # all centers
    uv run python scripts/kb_lint.py juniper-hill    # one center
    uv run python scripts/kb_lint.py --json          # machine-readable

Findings by confidence:
- duplicate / ambiguous_duplicate: the literal is an identifier (phone, email, person's name) or a
  money amount matching one / several keyed values. These fail the lint.
- possible_duplicate: a time or fact value ("3:30 PM", "24 hours"). Equal values are often
  different facts (fever-free 24 hours vs symptom-free 24 hours), so these are listed for review
  and don't fail the lint. This is also why auto-fixing is restricted (KNOWLEDGE_MAINTENANCE.md §3).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402
from app.lint import lint_center  # noqa: E402


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    slugs = [a for a in argv if not a.startswith("--")]
    with db.connect() as conn:
        slugs = slugs or [r["slug"] for r in db.rows(conn, "SELECT slug FROM centers ORDER BY slug")]
        findings = [f for s in slugs for f in lint_center(conn, s)]
    if as_json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            hint = f" -> {', '.join(f['candidates'])}" if f["candidates"] else ""
            print(f"{f['center']:15} {f['section']:28} {f['kind']:20} {f['literal']!r}{hint}")
        failing = [f for f in findings if f["kind"] != "possible_duplicate"]
        print(f"{len(failing)} failing, {len(findings) - len(failing)} to review, across {len(slugs)} center(s).")
    return 1 if any(f["kind"] != "possible_duplicate" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
