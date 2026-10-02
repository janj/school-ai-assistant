"""Run every question in seed/<slug>/eval_questions.md against a running server.

    uv run python scripts/run_evals.py                                   # local server, all centers
    uv run python scripts/run_evals.py juniper-hill --only 3,N1,F2       # some questions
    uv run python scripts/run_evals.py --base-url https://162-243-171-212.sslip.io
    uv run python scripts/run_evals.py --compare data/evals/<earlier>.json

Each answer is checked automatically for the parts that can be checked mechanically:
- the `found` flag matches the section (answerable → true, not answerable → false; the
  "Operator questions" table states it per row: yes / no / either);
- a not-found answer carries the server-added contact card;
- Spanish questions get a Spanish answer (simple heuristic).
Whether the *content* is right is for a person to judge: the report prints question, expected
answer and actual answer side by side. Results are saved to data/evals/<timestamp>.json.

Follow-up pairs run as a real two-turn conversation (same conversation_id).

Costs real API calls (~70 questions, a few cents with prompt caching). The live server allows
20 requests per 5 minutes per IP, so a full live run waits out 429s; for quick iteration run
locally with raised limits:
    RATE_LIMIT_REQUESTS=500 TOKEN_BUDGET_SHORT=2000000 TOKEN_BUDGET_DAILY=5000000 \\
        ANTHROPIC_API_KEY=... uv run uvicorn app.main:app --port 8000
Exit code 1 if any automatic check fails.
"""

import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPANISH_HINT = re.compile(r"[¿¡ñ]|\b(el|la|los|las|de|que|por|para|está|centro|niño|horario)\b", re.I)


# ---- parsing eval_questions.md --------------------------------------------------------------
def parse(path: Path) -> list[dict]:
    """Rows of every table, tagged with the section they came from."""
    items, section, header = [], "", []
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            section, header = line[3:].strip(), []
            continue
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not header:
            header = [c.lower() for c in cells]
            continue
        row = dict(zip(header, cells))
        qid = row.get("#", "")
        if not qid:
            continue
        kind = ("unanswerable" if section.lower().startswith("not answerable") else
                "followup" if section.lower().startswith("follow-up") else
                "spanish" if section.lower().startswith("spanish") else
                "operator" if section.lower().startswith("operator") else "answerable")
        expected_found = {"unanswerable": "no", "operator": (row.get("found") or "either").lower()}.get(kind, "yes")
        items.append({"id": qid, "kind": kind, "question": row.get("question", "").strip("*` "),
                      "followup": row.get("follow-up", "").strip("*` ") or None,
                      "expected": row.get("expected answer") or row.get("expected") or row.get("notes") or "",
                      "expected_found": expected_found})
    return items


# ---- talking to the server ------------------------------------------------------------------
class Client:
    def __init__(self, base: str, slug: str):
        self.base = base.rstrip("/")
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        status, body = self._post("/api/session", {"role": "parent", "center_slug": slug})
        if status != 200:
            raise SystemExit(f"Could not start a session for {slug}: {status} {body}")

    def _post(self, path: str, body: dict) -> tuple[int, dict]:
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(),
                                     {"content-type": "application/json"})
        try:
            with self.opener.open(req, timeout=120) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def ask(self, message: str, conversation_id: str) -> tuple[int, dict]:
        for attempt in range(12):
            status, body = self._post("/api/chat", {"message": message, "conversation_id": conversation_id})
            if status != 429:
                return status, body
            print(f"    rate limited ({body.get('kind')}); waiting 30s…", file=sys.stderr)
            time.sleep(30)
        return status, body


# ---- checks ---------------------------------------------------------------------------------
def check(item: dict, status: int, r: dict) -> list[str]:
    problems = []
    if status != 200:
        return [f"HTTP {status}: {r.get('detail')}"]
    want = item["expected_found"]
    if want in ("yes", "no") and r.get("found") != (want == "yes"):
        problems.append(f"found={r.get('found')}, expected {want}")
    if r.get("found") is False and not r.get("contact"):
        problems.append("not found but no contact card")
    if item["kind"] == "spanish" and not SPANISH_HINT.search(r.get("answer", "")):
        problems.append("answer doesn't look Spanish")
    return problems


def run_center(base: str, slug: str, only: set[str] | None) -> list[dict]:
    client = Client(base, slug)
    out = []
    for item in parse(ROOT / "seed" / slug / "eval_questions.md"):
        if only and item["id"] not in only:
            continue
        conv = str(uuid.uuid4())  # each question (or pair) is its own conversation
        turns = [item["question"]] + ([item["followup"]] if item["followup"] else [])
        for n, message in enumerate(turns):
            status, r = client.ask(message, conv)
            result = {"center": slug, "id": item["id"] + ("b" if n else ""), "kind": item["kind"],
                      "question": message, "expected": item["expected"] if n == len(turns) - 1 else "",
                      "status": status, "found": r.get("found"), "sources": r.get("sources"),
                      "answer": r.get("answer") or r.get("detail") or "",
                      "contact": r.get("contact")}
            result["problems"] = check({**item, "expected_found": item["expected_found"]}, status, r)
            mark = "FAIL" if result["problems"] else "ok  "
            print(f"{mark} {slug:14} {result['id']:>4}  {message[:70]}")
            out.append(result)
    return out


def report(results: list[dict], previous: list[dict] | None) -> None:
    print("\n" + "=" * 100)
    for r in results:
        flag = "FAIL: " + "; ".join(r["problems"]) if r["problems"] else f"found={r['found']} {r['sources']}"
        print(f"\n[{r['center']} {r['id']}] {r['question']}\n  {flag}")
        if r["expected"]:
            print(f"  expected: {r['expected']}")
        print(f"  answer:   {' '.join(r['answer'].split())[:400]}")
    if previous is not None:
        before = {(p["center"], p["id"]): p for p in previous}
        changed = [r for r in results if (r["center"], r["id"]) in before
                   and before[(r["center"], r["id"])]["found"] != r["found"]]
        print("\nfound-flag changes vs previous run:",
              [(r["center"], r["id"], before[(r["center"], r["id"])]["found"], r["found"]) for r in changed] or "none")
    failing = [r for r in results if r["problems"]]
    print(f"\n{len(results) - len(failing)}/{len(results)} passed the automatic checks.")
    for r in failing:
        print(f"  FAIL {r['center']} {r['id']}: {'; '.join(r['problems'])}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("centers", nargs="*", help="center slugs (default: every seed/<slug>/eval_questions.md)")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--only", help="comma-separated question ids, e.g. 3,N1,F2,O4")
    ap.add_argument("--compare", help="an earlier results JSON to diff found-flags against")
    args = ap.parse_args()

    slugs = args.centers or sorted(p.parent.name for p in (ROOT / "seed").glob("*/eval_questions.md")
                                   if not p.parent.name.startswith("_"))
    only = set(args.only.split(",")) if args.only else None
    results = [r for slug in slugs for r in run_center(args.base_url, slug, only)]

    previous = json.loads(Path(args.compare).read_text()) if args.compare else None
    report(results, previous)
    out_dir = ROOT / "data" / "evals"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(f"Saved {out.relative_to(ROOT)}")
    return 1 if any(r["problems"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
