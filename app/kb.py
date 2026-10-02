"""Renders one center's knowledge base into prompt text.

Contract (docs/CONTRACTS.md §4): every section starts with a line `[section: <id>]`.
Section IDs: center, contacts, hours, closures, schedule, fees, lunch_menu,
policy:<topic>, faq:<id>. section_ids() returns exactly the IDs present.

Rendered fresh on every call (a few small SQLite queries) so admin edits, which happen
in another module, are always visible. Output is deterministic: fixed ordering, no timestamps.
"""

import re
from datetime import date, datetime

from app import db

_SECTION_RE = re.compile(r"^\[section: (.+)\]$", re.MULTILINE)


def _time(value: str | None) -> str:
    if not value:
        return ""
    return datetime.strptime(value, "%H:%M").strftime("%I:%M %p").lstrip("0")


def _money(cents: int | None) -> str:
    return "" if cents is None else f"${cents / 100:,.2f}"


def _day(value: str) -> str:
    d = date.fromisoformat(value)
    return f"{d.strftime('%A %B')} {d.day}, {d.year}"


def _span(start: str | None, end: str | None) -> str:
    if start and end:
        return f"{_time(start)} - {_time(end)}"
    return _time(start) or _time(end)


def _note(text: str | None) -> str:
    return f" ({text})" if text else ""


def _sections(slug: str) -> list[tuple[str, str]]:
    with db.connect() as conn:
        def q(sql):
            return db.rows(conn, sql, (slug,))

        center = q("SELECT * FROM centers WHERE slug = ?")
        contacts = q("SELECT * FROM contacts WHERE center_slug = ? ORDER BY sort_order, id")
        hours = q("SELECT * FROM hours WHERE center_slug = ? ORDER BY id")
        closures = q("SELECT * FROM closures WHERE center_slug = ? ORDER BY start_date, id")
        blocks = q("SELECT * FROM schedule_blocks WHERE center_slug = ? ORDER BY age_group, start_time, id")
        fees = q("SELECT * FROM fees WHERE center_slug = ? ORDER BY category, id")
        lunch = q("SELECT * FROM lunch_menu WHERE center_slug = ? ORDER BY id")
        policies = q("SELECT * FROM policies WHERE center_slug = ? ORDER BY topic")
        faqs = q("SELECT * FROM faq WHERE center_slug = ? ORDER BY id")

    out: list[tuple[str, str]] = []
    if center:
        c = center[0]
        lines = [f"Name: {c['name']}"]
        for label, key in (("Tagline", "tagline"), ("Address", "address"),
                           ("Main phone", "main_phone"), ("Main email", "main_email"),
                           ("Website", "website")):
            if c[key]:
                lines.append(f"{label}: {c[key]}")
        out.append(("center", "\n".join(lines)))

    if contacts:
        lines = []
        for r in contacts:
            bits = [b for b in (r["phone"], r["email"]) if b]
            lines.append(f"- {r['position']}: {r['name']}" + (f" - {', '.join(bits)}" if bits else ""))
        out.append(("contacts", "\n".join(lines)))

    if hours:
        lines = []
        for r in hours:
            when = _span(r["open_time"], r["close_time"]) or "Closed"
            lines.append(f"- {r['days']}: {when}{_note(r['notes'])}")
        out.append(("hours", "\n".join(lines)))

    if closures:
        lines = []
        for r in closures:
            when = _day(r["start_date"])
            if r["end_date"]:
                when += f" to {_day(r['end_date'])}"
            lines.append(f"- {when}: {r['name']}{_note(r['notes'])}")
        out.append(("closures", "\n".join(lines)))

    if blocks:
        lines, group = [], None
        for r in blocks:
            if r["age_group"] != group:
                group = r["age_group"]
                lines.append(f"{group}:")
            lines.append(f"- {_span(r['start_time'], r['end_time'])}: {r['activity']}")
        out.append(("schedule", "\n".join(lines)))

    if fees:
        lines = []
        for r in fees:
            amount = _money(r["amount_cents"]) or "amount not listed"
            period = f" {r['period']}" if r["period"] else ""
            lines.append(f"- {r['category']} / {r['name']}: {amount}{period}{_note(r['notes'])}")
        out.append(("fees", "\n".join(lines)))

    if lunch:
        lines = [f"- {r['day']} {r['meal']}: {r['items']}{_note(r['notes'])}" for r in lunch]
        out.append(("lunch_menu", "\n".join(lines)))

    for p in policies:
        out.append((f"policy:{p['topic']}", f"{p['title']}\n{p['body_md'].strip()}"))
    for f in faqs:
        out.append((f"faq:{f['id']}", f"Q: {f['question']}\nA: {f['answer']}"))
    return out


def render_center_kb(center_slug: str) -> str:
    return "\n\n".join(f"[section: {sid}]\n{body}" for sid, body in _sections(center_slug))


def section_ids(center_slug: str) -> set[str]:
    return {sid for sid, _ in _sections(center_slug)}
