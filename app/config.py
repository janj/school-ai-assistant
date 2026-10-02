"""Environment-driven settings. Everything tunable lives here."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANSWER_MODEL = os.environ.get("ANSWER_MODEL", "claude-sonnet-5-5")
FAST_MODEL = os.environ.get("FAST_MODEL", "claude-haiku-4-5-20251001")

DB_PATH = Path(os.environ.get("DB_PATH", ROOT / "data" / "school.db"))
SEED_DIR = ROOT / "seed"
STATIC_DIR = ROOT / "static"

# Signs the session cookie. Must be set in production; the dev default is fine locally.
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-only-not-secret")
SESSION_COOKIE = "sa_session"

# Per-IP limits (Track B). IPs are held in memory only, never persisted.
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", 20))
RATE_LIMIT_WINDOW_S = int(os.environ.get("RATE_LIMIT_WINDOW_S", 300))
TOKEN_BUDGET_SHORT = int(os.environ.get("TOKEN_BUDGET_SHORT", 60_000))
TOKEN_BUDGET_SHORT_WINDOW_S = int(os.environ.get("TOKEN_BUDGET_SHORT_WINDOW_S", 600))
TOKEN_BUDGET_DAILY = int(os.environ.get("TOKEN_BUDGET_DAILY", 300_000))

MAX_MESSAGE_CHARS = 1000
