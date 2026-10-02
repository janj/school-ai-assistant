"""Knowledge-base lint: values typed into prose that already have a home, and broken placeholders.

Deterministic, no model calls. Reads the live database (default: data/school.db).
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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, fmt, placeholders  # noqa: E402

GENERIC_NAMES = {"front desk", "office", "front office"}  # directory rows that aren't people


def _money_variants(cents: int) -> set[str]:
    full = fmt.money(abs(cents))                       # $1,420.00
    return {full, full.removesuffix(".00"), full.replace(",", ""), full.replace(",", "").removesuffix(".00")}


CONFIDENT = {"identifier", "money"}  # equal value almost certainly means the same fact


def _needles(ctx: dict) -> dict[str, dict[str, str]]:
    """literal text -> {placeholder token it duplicates: value class}."""
    out: dict[str, dict[str, str]] = {}

    def add(literal, token, cls):
        if literal and len(literal) >= 3:
            out.setdefault(literal, {})[token] = cls

    for key, r in ctx["fee"].items():
        if r["amount_cents"]:
            for v in _money_variants(r["amount_cents"]):
                add(v, f"{{{{fee:{key}}}}}", "money")
    for key, r in ctx["contact"].items():
        add(r["phone"], f"{{{{contact:{key}.phone}}}}", "identifier")
        add(r["email"], f"{{{{contact:{key}.email}}}}", "identifier")
        if r["name"] and r["name"].lower() not in GENERIC_NAMES:
            add(r["name"].split(",")[0], f"{{{{contact:{key}}}}}", "identifier")  # "Rosalind Vega, RN"
    for key, r in ctx["hours"].items():
        add(fmt.time(r["open_time"]), f"{{{{hours:{key}.open}}}}", "time")
        add(fmt.time(r["close_time"]), f"{{{{hours:{key}.close}}}}", "time")
    for key, r in ctx["fact"].items():
        add(r["value"], f"{{{{fact:{key}}}}}", "fact")
    c = ctx["center"]
    add(c.get("main_phone"), "{{center:main_phone}}", "identifier")
    add(c.get("main_email"), "{{center:main_email}}", "identifier")
    return out


def lint_center(conn, slug: str) -> list[dict]:
    ctx = placeholders.context(conn, slug)
    needles = _needles(ctx)
    docs = [(f"policy:{r['topic']}", r["body_md"]) for r in
            db.rows(conn, "SELECT topic, body_md FROM policies WHERE center_slug = ? ORDER BY topic", (slug,))]
    docs += [(f"faq:{r['id']}", r["answer"]) for r in
             db.rows(conn, "SELECT id, answer FROM faq WHERE center_slug = ? ORDER BY id", (slug,))]
    findings = []
    for section, text in docs:
        for bad in dict.fromkeys(placeholders.invalid(text, ctx)):
            findings.append({"center": slug, "section": section, "kind": "broken_placeholder", "literal": bad,
                             "candidates": []})
        prose = placeholders.PATTERN.sub(" ", text or "")  # resolved values aren't duplicates
        for literal in sorted(needles, key=len, reverse=True):
            # Word-ish boundaries so "$15" doesn't match inside "$150", nor "5:30 PM" inside "15:30 PM".
            pattern = r"(?<![\w$.,])" + re.escape(literal) + r"(?![\w,]|\.\d)"
            if re.search(pattern, prose):
                prose = re.sub(pattern, " ", prose)  # longest first: don't re-report "$75" inside "$75.00"
                cands = sorted(needles[literal])
                if not CONFIDENT & set(needles[literal].values()):
                    kind = "possible_duplicate"
                else:
                    kind = "duplicate" if len(cands) == 1 else "ambiguous_duplicate"
                findings.append({"center": slug, "section": section, "kind": kind,
                                 "literal": literal, "candidates": cands})
    return findings


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
