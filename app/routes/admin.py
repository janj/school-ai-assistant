"""Admin data editor API: CRUD over app.registry, audit history, reset-to-seed.

All routes depend on session.require_admin and use the session's center_slug only.
Table and column names reach SQL only after being looked up in registry.EDITABLE.
"""

import json
import re
import sqlite3
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException

from app import config, db, placeholders, session as sess
from app.registry import EDITABLE

router = APIRouter(prefix="/api/admin")

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOPIC_RE = re.compile(r"^[a-z0-9_]+$")
# Text columns that may contain {{placeholders}}; validated on save.
PLACEHOLDER_FIELDS = {"policies": "body_md", "faq": "answer"}
# Keyed table -> placeholder type (inverse of placeholders.TABLES).
KEY_TYPES = {table: kind for kind, table in placeholders.TABLES.items()}


def _table(name: str) -> dict:
    if name not in EDITABLE:
        raise HTTPException(404, f"Unknown table '{name}'.")
    return EDITABLE[name]


def _cols(table: dict) -> list[dict]:
    return [{"name": n, "type": t, "label": label, "required": req}
            for n, t, label, req in table["columns"]]


def _select_sql(name: str, table: dict) -> str:
    key = "slug" if name == "centers" else "id"
    names = ", ".join(c["name"] for c in _cols(table))
    return f"SELECT {key} AS id, {names} FROM {name}"


def _get_row(conn, name: str, table: dict, row_id, center: str) -> dict | None:
    """The row, only if it belongs to `center` (centers: only the center's own row)."""
    if name == "centers":
        found = db.rows(conn, _select_sql(name, table) + " WHERE slug = ?", (center,))
        return found[0] if found and row_id == center else None
    found = db.rows(conn, _select_sql(name, table) + " WHERE id = ? AND center_slug = ?", (row_id, center))
    return found[0] if found else None


def _clean(col: dict, value):
    """Validate one value by column type; '' / None become None (required is checked by the caller)."""
    label, kind = col["label"], col["type"]
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if kind in ("int", "money_cents"):
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(400, f"{label} must be a whole number.")
        return value
    if not isinstance(value, str):
        raise HTTPException(400, f"{label} must be text.")
    if kind in ("text", "time", "date", "key"):
        value = value.strip()
    if kind == "key" and not placeholders.KEY_RE.match(value):
        raise HTTPException(400, f"{label} must use only lowercase letters, digits and underscores (e.g. late_pickup).")
    if kind == "time" and not TIME_RE.match(value):
        raise HTTPException(400, f"{label} must be a time like 14:30.")
    if kind == "date":
        try:
            if not DATE_RE.match(value):
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            raise HTTPException(400, f"{label} must be a date like 2026-11-26.")
    return value


def _validate(name: str, table: dict, body: dict, base: dict | None) -> dict:
    """Full column->value dict to store. On update, `base` (current row) sits under the body."""
    cols = {c["name"]: c for c in _cols(table)}
    unknown = sorted(set(body) - set(cols))
    if unknown:
        raise HTTPException(400, f"Unknown column(s): {', '.join(unknown)}.")
    merged = {n: (base or {}).get(n) for n in cols}
    merged.update(body)
    out = {}
    for n, col in cols.items():
        v = _clean(col, merged[n])
        if v is None and col["required"]:
            raise HTTPException(400, f"{col['label']} is required.")
        if v is None and col["type"] == "int":
            v = 0  # sort_order is NOT NULL DEFAULT 0
        out[n] = v
    if name == "policies" and not TOPIC_RE.match(out["topic"]):
        raise HTTPException(400, "Topic must use only lowercase letters, digits and underscores.")
    if base is not None and "key" in cols and out["key"] != base.get("key"):
        # Stable-key rule: placeholders elsewhere depend on this key never changing.
        raise HTTPException(400, "A key can't be changed after it is created. Add a new row instead.")
    return out


def _check_placeholders(conn, name: str, values: dict, center: str) -> None:
    field = PLACEHOLDER_FIELDS.get(name)
    if not field:
        return
    bad = placeholders.invalid(values.get(field), placeholders.context(conn, center))
    if bad:
        raise HTTPException(400, f"Unknown placeholder(s): {', '.join(dict.fromkeys(bad))}. "
                                 "Check the key exists, or pick one from the placeholder list.")


def _users_of(conn, center: str, kind: str, key: str) -> list[str]:
    """Policies/FAQs whose text references {{kind:key...}}."""
    users = []
    for r in db.rows(conn, "SELECT topic, body_md FROM policies WHERE center_slug = ?", (center,)):
        if (kind, key) in placeholders.references(r["body_md"]):
            users.append(f"policy '{r['topic']}'")
    for r in db.rows(conn, "SELECT id, answer FROM faq WHERE center_slug = ?", (center,)):
        if (kind, key) in placeholders.references(r["answer"]):
            users.append(f"FAQ #{r['id']}")
    return users


def _key_conflict(table: str, values: dict):
    return HTTPException(409, f"The key '{values.get('key')}' is already used in {EDITABLE[table]['label']}.")


def _audit(conn, session: dict, table: str, row_id, action: str, before, after) -> None:
    conn.execute(
        "INSERT INTO audit_log (center_slug, admin_name, table_name, row_id, action, before_json, after_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session["center_slug"], session["display_name"] or "admin", table,
         row_id if isinstance(row_id, int) else None, action,
         json.dumps(before) if before is not None else None,
         json.dumps(after) if after is not None else None),
    )


def _topic_taken(conn, center: str, topic: str, exclude_id=None) -> bool:
    found = db.rows(conn, "SELECT id FROM policies WHERE center_slug = ? AND topic = ?", (center, topic))
    return any(r["id"] != exclude_id for r in found)


def _int_id(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(404, "Row not found.")


@router.get("/registry")
def registry(_s: dict = Depends(sess.require_admin)):
    return {name: {**{k: v for k, v in t.items() if k != "columns"}, "columns": _cols(t)}
            for name, t in EDITABLE.items()}


@router.get("/data/{table}")
def list_rows(table: str, s: dict = Depends(sess.require_admin)):
    t = _table(table)
    with db.connect() as conn:
        if table == "centers":
            return db.rows(conn, _select_sql(table, t) + " WHERE slug = ?", (s["center_slug"],))
        return db.rows(conn, _select_sql(table, t) + " WHERE center_slug = ? ORDER BY " + t["order_by"],
                       (s["center_slug"],))


@router.post("/data/{table}")
def create_row(table: str, body: dict = Body(...), s: dict = Depends(sess.require_admin)):
    t = _table(table)
    if t.get("single_row"):
        raise HTTPException(405, "Rows can't be added to this table.")
    values = _validate(table, t, body, None)
    center = s["center_slug"]
    if table == "faq":
        values["created_by"] = s["display_name"]
    cols = list(values)
    with db.connect() as conn:
        if table == "policies" and _topic_taken(conn, center, values["topic"]):
            raise HTTPException(409, f"A policy with the topic '{values['topic']}' already exists.")
        _check_placeholders(conn, table, values, center)
        try:
            cur = conn.execute(
                f"INSERT INTO {table} (center_slug, {', '.join(cols)}) VALUES (?, {', '.join('?' * len(cols))})",
                (center, *values.values()),
            )
        except sqlite3.IntegrityError:
            raise _key_conflict(table, values)
        row = _get_row(conn, table, t, cur.lastrowid, center)
        _audit(conn, s, table, cur.lastrowid, "create", None, row)
    return row


@router.put("/data/{table}/{row_id}")
def update_row(table: str, row_id: str, body: dict = Body(...), s: dict = Depends(sess.require_admin)):
    t = _table(table)
    center = s["center_slug"]
    key = row_id if table == "centers" else _int_id(row_id)
    with db.connect() as conn:
        before = _get_row(conn, table, t, key, center)
        if not before:
            raise HTTPException(404, "Row not found.")
        values = _validate(table, t, body, before)
        if table == "policies" and _topic_taken(conn, center, values["topic"], exclude_id=key):
            raise HTTPException(409, f"A policy with the topic '{values['topic']}' already exists.")
        _check_placeholders(conn, table, values, center)
        sets = ", ".join(f"{c} = ?" for c in values)
        if table == "centers":
            cur = conn.execute(f"UPDATE centers SET {sets} WHERE slug = ?", (*values.values(), center))
        else:
            cur = conn.execute(f"UPDATE {table} SET {sets} WHERE id = ? AND center_slug = ?",
                               (*values.values(), key, center))
        if cur.rowcount != 1:
            raise HTTPException(404, "Row not found.")
        after = _get_row(conn, table, t, key, center)
        _audit(conn, s, table, key if isinstance(key, int) else None, "update", before, after)
    return after


@router.delete("/data/{table}/{row_id}")
def delete_row(table: str, row_id: str, s: dict = Depends(sess.require_admin)):
    t = _table(table)
    if t.get("single_row"):
        raise HTTPException(405, "This row can't be deleted.")
    key = _int_id(row_id)
    center = s["center_slug"]
    with db.connect() as conn:
        before = _get_row(conn, table, t, key, center)
        if not before:
            raise HTTPException(404, "Row not found.")
        if table in KEY_TYPES and before.get("key"):
            users = _users_of(conn, center, KEY_TYPES[table], before["key"])
            if users:
                raise HTTPException(409, f"'{before['key']}' is used by {', '.join(users)}. "
                                         "Remove those placeholders first.")
        cur = conn.execute(f"DELETE FROM {table} WHERE id = ? AND center_slug = ?", (key, center))
        if cur.rowcount != 1:
            raise HTTPException(404, "Row not found.")
        _audit(conn, s, table, key, "delete", before, None)
    return {"ok": True}


@router.get("/placeholders")
def list_placeholders(s: dict = Depends(sess.require_admin)):
    """Every placeholder available to this center, with its current value (for the editor picker)."""
    with db.connect() as conn:
        return placeholders.catalog(placeholders.context(conn, s["center_slug"]))


@router.post("/preview")
def preview(body: dict = Body(...), s: dict = Depends(sess.require_admin)):
    """Text with placeholders resolved exactly as the assistant will see it."""
    text = body.get("text")
    if not isinstance(text, str):
        raise HTTPException(400, "Send {\"text\": \"...\"}.")
    with db.connect() as conn:
        ctx = placeholders.context(conn, s["center_slug"])
    rendered, _ = placeholders.render(text, ctx)
    return {"rendered": rendered, "invalid": list(dict.fromkeys(placeholders.invalid(text, ctx)))}


@router.get("/history")
def history(limit: int = 50, offset: int = 0, s: dict = Depends(sess.require_admin)):
    limit = max(1, min(limit, 200))
    with db.connect() as conn:
        return db.rows(
            conn,
            "SELECT id, admin_name, table_name, row_id, action, before_json, after_json, created_at"
            " FROM audit_log WHERE center_slug = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (s["center_slug"], limit, max(0, offset)),
        )


@router.post("/reset")
def reset(body: dict = Body(...), s: dict = Depends(sess.require_admin)):
    if body.get("confirm") != "RESET":
        raise HTTPException(400, 'Send {"confirm": "RESET"} to reset this center.')
    slug = s["center_slug"]
    seed_dir = slug
    if not (config.SEED_DIR / slug / "center.json").exists():
        # Placeholder seed (_example) is used only while no real seeds exist; its dir name != slug.
        example = config.SEED_DIR / "_example" / "center.json"
        if db.seed_slugs() == ["_example"] and example.exists() and json.loads(example.read_text())["slug"] == slug:
            seed_dir = "_example"
        else:
            raise HTTPException(404, "No seed data exists for this center.")
    db.load_seed(seed_dir)
    with db.connect() as conn:
        _audit(conn, s, "*", None, "reset", None, None)
    return {"ok": True}
