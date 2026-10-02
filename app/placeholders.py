"""Placeholders: one home per fact (docs/KNOWLEDGE_MAINTENANCE.md §2).

Policy and FAQ text may contain `{{type:key}}` or `{{type:key.field}}`; they are resolved from the
center's keyed rows when the KB is rendered. Keys are unique per center and immutable after
creation (enforced in routes/admin.py), which is what makes a reference stable.

    {{fee:registration}}        -> $75.00          (fields: amount, name, period, notes)
    {{contact:nurse.phone}}     -> (505) 555-0124  (fields: name, phone, email, position)
    {{hours:weekdays.close}}    -> 6:00 PM         (fields: span, open, close, days)
    {{fact:fever_threshold}}    -> 100.4°F         (fields: value, label)
    {{center:main_phone}}       -> center row field (name, main_phone, main_email, address, website, tagline)
"""

import re

from app import db, fmt

PATTERN = re.compile(r"\{\{\s*(fee|contact|hours|fact|center):([a-z0-9_]+)(?:\.([a-z_]+))?\s*\}\}")
KEY_RE = re.compile(r"^[a-z0-9_]+$")
MISSING = "(not listed)"

# Keyed tables, and how each field of a row renders. The first field is the default.
FIELDS = {
    "fee": {"amount": lambda r: fmt.money(r["amount_cents"]), "name": lambda r: r["name"],
            "period": lambda r: r["period"], "notes": lambda r: r["notes"]},
    "contact": {"name": lambda r: r["name"], "phone": lambda r: r["phone"], "email": lambda r: r["email"],
                "position": lambda r: r["position"]},
    "hours": {"span": lambda r: fmt.span(r["open_time"], r["close_time"]) or "Closed",
              "open": lambda r: fmt.time(r["open_time"]), "close": lambda r: fmt.time(r["close_time"]),
              "days": lambda r: r["days"]},
    "fact": {"value": lambda r: r["value"], "label": lambda r: r["label"]},
}
TABLES = {"fee": "fees", "contact": "contacts", "hours": "hours", "fact": "facts"}
CENTER_FIELDS = ("name", "main_phone", "main_email", "address", "website", "tagline")


def context(conn, slug: str) -> dict:
    """{type: {key: row}} for one center, plus the center row under 'center'."""
    ctx = {t: {r["key"]: r for r in db.rows(conn, f"SELECT * FROM {table} WHERE center_slug = ? AND key IS NOT NULL",
                                            (slug,))}
           for t, table in TABLES.items()}
    center = db.rows(conn, "SELECT * FROM centers WHERE slug = ?", (slug,))
    ctx["center"] = center[0] if center else {}
    return ctx


def _lookup(ctx: dict, kind: str, key: str, field: str | None) -> str | None:
    """Rendered value, or None if the reference doesn't resolve."""
    if kind == "center":
        if field or key not in CENTER_FIELDS:  # {{center:main_phone}} only
            return None
        return ctx["center"].get(key) or None
    row = ctx[kind].get(key)
    fields = FIELDS[kind]
    if row is None or (field and field not in fields):
        return None
    value = fields[field or next(iter(fields))](row)
    return value or None


def render(text: str, ctx: dict) -> tuple[str, list[str]]:
    """Resolve every placeholder. Unresolvable ones become MISSING (never left for the model to guess)."""
    missing = []

    def sub(m):
        value = _lookup(ctx, *m.groups())
        if value is None:
            missing.append(m.group(0))
            return MISSING
        return value

    return PATTERN.sub(sub, text or ""), missing


def invalid(text: str, ctx: dict) -> list[str]:
    """Placeholders in `text` that don't resolve (unknown key or field), plus malformed `{{...}}`."""
    bad = [m.group(0) for m in PATTERN.finditer(text or "") if _lookup(ctx, *m.groups()) is None]
    # Anything brace-shaped that isn't a well-formed placeholder is almost certainly a typo.
    bad += [m.group(0) for m in re.finditer(r"\{\{[^}]*\}\}", text or "") if not PATTERN.fullmatch(m.group(0))]
    return bad


def references(text: str) -> set[tuple[str, str]]:
    """{(type, key)} used by `text` (center fields excluded: that row can't be deleted)."""
    return {(m.group(1), m.group(2)) for m in PATTERN.finditer(text or "") if m.group(1) != "center"}


def catalog(ctx: dict) -> list[dict]:
    """Every available placeholder with its current value, for the admin picker."""
    out = []
    for kind, rows in ctx.items():
        if kind == "center":
            out += [{"token": f"{{{{center:{f}}}}}", "value": rows.get(f) or "", "group": "Center"}
                    for f in CENTER_FIELDS]
            continue
        for key, row in sorted(rows.items()):
            for i, field in enumerate(FIELDS[kind]):
                token = f"{{{{{kind}:{key}}}}}" if i == 0 else f"{{{{{kind}:{key}.{field}}}}}"
                out.append({"token": token, "value": FIELDS[kind][field](row) or "", "group": TABLES[kind]})
    return out
