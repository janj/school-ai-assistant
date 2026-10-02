"""Run the knowledge maintenance agent (docs/KNOWLEDGE_MAINTENANCE.md §3).

    uv run python scripts/maintain_kb.py --all --rules-only      # nightly: free checks
    uv run python scripts/maintain_kb.py --all                   # weekly: rules + AI review
    uv run python scripts/maintain_kb.py juniper-hill --dry-run  # show what it would do, write nothing
    uv run python scripts/maintain_kb.py --all --json

The AI review needs ANTHROPIC_API_KEY. Exit code is 0 unless a run raised or the AI check failed.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, maintenance  # noqa: E402


def _print(s: dict) -> None:
    opened = s.get("issues_opened", s.get("would_open"))
    resolved = s.get("issues_resolved", s.get("would_resolve"))
    tag = " (dry run)" if s["dry_run"] else ""
    print(f"{s['center']}{tag}")
    print(f"  checks:      {', '.join(s['checks']) or 'none'}")
    print(f"  auto-fixes:  {len(s['auto_fixes'])}")
    for f in s["auto_fixes"]:
        print(f"    {f['section']}: {f['literal']!r} -> {f['token']}")
    for f in s["not_fixed"]:
        print(f"    left for review: {f['section']} {f['literal']!r} ({f['reason']})")
    print(f"  issues:      {opened} opened, {resolved} resolved, {s['issues_open_total']} open now")
    if s["usage"]:
        print(f"  ai tokens:   {s['usage']}")
    if s["ai_error"]:
        print(f"  AI check failed: {s['ai_error']}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slugs", nargs="*", help="center slugs")
    ap.add_argument("--all", action="store_true", help="every center")
    ap.add_argument("--rules-only", action="store_true", help="skip the AI review")
    ap.add_argument("--dry-run", action="store_true", help="write nothing")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    if not args.slugs and not args.all:
        ap.error("give center slugs or --all")
    db.init_db()  # makes sure kb_issues exists on an older database
    with db.connect() as conn:
        slugs = [r["slug"] for r in db.rows(conn, "SELECT slug FROM centers ORDER BY slug")] if args.all else args.slugs
    results, failed = [], False
    for slug in slugs:
        try:
            s = maintenance.run(slug, rules=True, ai=not args.rules_only, dry_run=args.dry_run)
        except ValueError as e:
            print(f"{slug}: {e}", file=sys.stderr)
            failed = True
            continue
        failed |= bool(s["ai_error"])
        results.append(s)
        if not args.json:
            _print(s)
    if args.json:
        print(json.dumps(results, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
