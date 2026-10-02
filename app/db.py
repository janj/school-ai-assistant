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
}
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
        existing = {r["slug"] for r in rows(conn, "SELECT slug FROM centers")}
    for slug in seed_slugs():
        if slug not in existing:
            load_seed(slug)


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
