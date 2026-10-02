"""SQLite access, schema init and seed loading.

One file, one writer process. Connections are opened per call (cheap for SQLite) so
handlers never share a connection across threads.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app import config

# Tenant tables loaded from seed/<slug>/<table>.json, in load order.
SEED_TABLES = {
    "contacts": "contacts.json",
    "hours": "hours.json",
    "closures": "closures.json",
    "schedule_blocks": "schedule.json",
    "fees": "fees.json",
    "lunch_menu": "lunch.json",
    "facts": "facts.json",
}
# Tables whose rows carry a stable `key` for placeholders (app/placeholders.py).
KEYED_TABLES = ["contacts", "hours", "fees", "facts"]
# Content tables wiped on a reset-to-seed (faq included: admin-authored KB entries).
RESETTABLE_TABLES = [*SEED_TABLES, "policies", "faq"]


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rows(conn, sql, params=()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def init_db() -> None:
    """Create tables; load seeds for any center not yet in the DB."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = (Path(__file__).parent / "schema.sql").read_text()
    with connect() as conn:
        conn.executescript(schema)
        reseed = _migrate(conn)
        existing = {r["slug"] for r in rows(conn, "SELECT slug FROM centers")}
    for slug in seed_slugs():
        if slug not in existing or slug in reseed:
            load_seed(slug)
    _sync_themes()


def _sync_themes() -> None:
    """Themes aren't admin-editable, so seed/<slug>/center.json is their only source: re-apply on
    every start so theme changes ship with a deploy (other center fields keep admin edits)."""
    with connect() as conn:
        for slug in seed_slugs():
            center = json.loads((config.SEED_DIR / slug / "center.json").read_text())
            conn.execute("UPDATE centers SET theme_json = ? WHERE slug = ?",
                         (json.dumps(center.get("theme", {})), center["slug"]))


def _migrate(conn) -> set[str]:
    """Bring an older database up to the current schema. Returns centers that must be re-seeded.

    Phase 3.0 added `key` to contacts/hours/fees. Rows from before then have no keys, and
    placeholders can't resolve without them, so those centers are reloaded from seed (POC: any
    admin edits to them are lost; the audit log is kept).
    """
    reseed = set()
    for table in ("contacts", "hours", "fees"):
        cols = {r["name"] for r in rows(conn, f"PRAGMA table_info({table})")}
        if "key" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN key TEXT")
            reseed |= {r["center_slug"] for r in rows(conn, f"SELECT DISTINCT center_slug FROM {table}")}
    for table in KEYED_TABLES:
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {table}_center_key ON {table} (center_slug, key)")
    return reseed


def seed_slugs() -> list[str]:
    """Center seed dirs. `_example` is only used when no real seed exists yet."""
    dirs = sorted(p.name for p in config.SEED_DIR.iterdir()
                  if p.is_dir() and not p.name.startswith("_"))
    return dirs or ["_example"]


def load_seed(slug: str) -> None:
    """(Re)load one center from seed/<slug>/, replacing its content rows.

    Sessions, qa_log and audit_log are left alone. Used by init_db and admin reset.
    """
    d = config.SEED_DIR / slug
    center = json.loads((d / "center.json").read_text())
    center_slug = center["slug"]
    with connect() as conn:
        for table in RESETTABLE_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE center_slug = ?", (center_slug,))
        conn.execute(
            """INSERT INTO centers (slug, name, tagline, address, main_phone, main_email, website, theme_json)
               VALUES (:slug, :name, :tagline, :address, :main_phone, :main_email, :website, :theme_json)
               ON CONFLICT(slug) DO UPDATE SET name=excluded.name, tagline=excluded.tagline,
                 address=excluded.address, main_phone=excluded.main_phone, main_email=excluded.main_email,
                 website=excluded.website, theme_json=excluded.theme_json""",
            {"tagline": None, "address": None, "website": None, **center,
             "theme_json": json.dumps(center.get("theme", {}))},
        )
        for table, filename in SEED_TABLES.items():
            f = d / filename
            if not f.exists():
                continue
            for row in json.loads(f.read_text()):
                cols = ["center_slug", *row.keys()]
                conn.execute(
                    f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                    (center_slug, *row.values()),
                )
        for md in sorted((d / "policies").glob("*.md")):
            title, body = _split_title(md.read_text())
            conn.execute(
                "INSERT INTO policies (center_slug, topic, title, body_md) VALUES (?, ?, ?, ?)",
                (center_slug, md.stem, title, body),
            )


def _split_title(text: str) -> tuple[str, str]:
    """Policy files start with '# Title'; the rest is the body."""
    first, _, rest = text.strip().partition("\n")
    return first.lstrip("# ").strip(), rest.strip()
