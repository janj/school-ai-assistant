-- School AI Assistant schema. Contract: see docs/CONTRACTS.md. Tracks may not change this file.
-- Every tenant table carries center_slug; handlers take it only from the session.

CREATE TABLE IF NOT EXISTS centers (
    slug        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    tagline     TEXT,
    address     TEXT,
    main_phone  TEXT NOT NULL,
    main_email  TEXT NOT NULL,
    website     TEXT,
    theme_json  TEXT NOT NULL DEFAULT '{}'   -- {"primary","accent","background","font","logo_text"}
);

-- Directory: position, name, phone (+ email)
CREATE TABLE IF NOT EXISTS contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug TEXT NOT NULL REFERENCES centers(slug),
    name        TEXT NOT NULL,
    position    TEXT NOT NULL,
    phone       TEXT,
    email       TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Hours of operation
CREATE TABLE IF NOT EXISTS hours (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug TEXT NOT NULL REFERENCES centers(slug),
    days        TEXT NOT NULL,              -- e.g. "Monday-Friday", "Saturday"
    open_time   TEXT,                       -- "07:00" (24h); NULL = closed
    close_time  TEXT,                       -- "18:00"
    notes       TEXT
);

-- Closure dates (single day: end_date NULL)
CREATE TABLE IF NOT EXISTS closures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug TEXT NOT NULL REFERENCES centers(slug),
    start_date  TEXT NOT NULL,              -- ISO "2026-11-26"
    end_date    TEXT,
    name        TEXT NOT NULL,              -- "Thanksgiving"
    notes       TEXT
);

-- Daily schedule, per age group
CREATE TABLE IF NOT EXISTS schedule_blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug TEXT NOT NULL REFERENCES centers(slug),
    age_group   TEXT NOT NULL,              -- "Infants", "Toddlers", "Preschool", "All"
    start_time  TEXT NOT NULL,              -- "08:30"
    end_time    TEXT,
    activity    TEXT NOT NULL
);

-- Fees
CREATE TABLE IF NOT EXISTS fees (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug  TEXT NOT NULL REFERENCES centers(slug),
    category     TEXT NOT NULL,             -- "Tuition", "Registration", "Late pickup", ...
    name         TEXT NOT NULL,
    amount_cents INTEGER,
    period       TEXT,                      -- "monthly", "weekly", "one-time", "per minute", ...
    notes        TEXT
);

-- Lunch menu
CREATE TABLE IF NOT EXISTS lunch_menu (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug TEXT NOT NULL REFERENCES centers(slug),
    day         TEXT NOT NULL,              -- "Monday" or "Week 1 Monday"
    meal        TEXT NOT NULL,              -- "Breakfast", "Lunch", "PM Snack"
    items       TEXT NOT NULL,
    notes       TEXT
);

-- Unstructured policy sections (markdown)
CREATE TABLE IF NOT EXISTS policies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug TEXT NOT NULL REFERENCES centers(slug),
    topic       TEXT NOT NULL,              -- slug, see CONTRACTS.md policy topics
    title       TEXT NOT NULL,
    body_md     TEXT NOT NULL,
    UNIQUE (center_slug, topic)
);

-- Admin-authored answers to previously unanswered questions (Phase 3, Track H)
CREATE TABLE IF NOT EXISTS faq (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug   TEXT NOT NULL REFERENCES centers(slug),
    question      TEXT NOT NULL,
    answer        TEXT NOT NULL,
    source_qa_id  INTEGER,
    created_by    TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Mocked sessions
CREATE TABLE IF NOT EXISTS sessions (
    id           TEXT PRIMARY KEY,          -- random token, referenced by signed cookie
    role         TEXT NOT NULL CHECK (role IN ('parent', 'admin')),
    center_slug  TEXT NOT NULL REFERENCES centers(slug),
    display_name TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Q/A log: scrubbed text only, never IPs
CREATE TABLE IF NOT EXISTS qa_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug       TEXT NOT NULL,
    session_id        TEXT,
    conversation_id   TEXT,
    role              TEXT,
    question          TEXT NOT NULL,        -- PII-scrubbed
    rewritten_query   TEXT,                 -- PII-scrubbed (Phase 3)
    answer            TEXT NOT NULL,        -- PII-scrubbed
    found             INTEGER NOT NULL,     -- 0/1
    sources_json      TEXT NOT NULL DEFAULT '[]',
    model             TEXT,
    input_tokens      INTEGER,
    output_tokens     INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    latency_ms        INTEGER,
    resolved_faq_id   INTEGER,              -- set when an admin answers it (Track H)
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS qa_log_center_created ON qa_log (center_slug, created_at);

-- Admin change history
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    center_slug TEXT NOT NULL,
    admin_name  TEXT NOT NULL,
    table_name  TEXT NOT NULL,
    row_id      INTEGER,
    action      TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete', 'reset')),
    before_json TEXT,
    after_json  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS audit_log_center_created ON audit_log (center_slug, created_at);
