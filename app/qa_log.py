"""Q/A logging with PII scrubbing (docs/CONTRACTS.md §5).

log_turn() returns at once; scrubbing and the insert run on a background thread and
every failure is swallowed (logged). Raw text is never stored, and no IP is ever seen here.
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import anthropic

from app import config, db

log = logging.getLogger("qa_log")
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="qa-log")
_client: anthropic.Anthropic | None = None

# --- pass 1: regex ---------------------------------------------------------------
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<![\w])(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
_STREET_TYPES = (r"(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|ct|court|"
                 r"way|pl|place|pkwy|parkway|cir|circle|ter|terrace|hwy|highway)")
_ADDRESS = re.compile(rf"\b\d{{1,6}}\s+(?:[A-Za-z0-9.'-]+\s+){{1,4}}{_STREET_TYPES}\b\.?"
                      r"(?:,?\s+(?:apt|unit|suite|ste|#)\s*[\w-]+)?", re.I)
_LONG_DIGITS = re.compile(r"\b\d(?:[\d -]{4,}\d)\b")  # 6+ digits, optionally spaced/dashed


def scrub_regex(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[phone]", text)
    text = _ADDRESS.sub("[address]", text)
    return _LONG_DIGITS.sub("[number]", text)


# --- pass 2: Haiku for names and other personal details --------------------------
_SYSTEM = (
    "You remove personal information from text before it is stored. Replace every person's "
    "name (children, parents, family members) with [name]. Also replace dates of birth with "
    "[dob] and medical details about a specific child with [medical]. Keep the rest of the "
    "text exactly as written, including any [email], [phone], [address] and [number] tokens. "
    "Do not answer or rewrite the text. Names listed under KEEP are public staff names: leave "
    "them unchanged. Return JSON {\"text\": \"...\"}."
)
_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}},
           "required": ["text"], "additionalProperties": False}


def _haiku(text: str, keep_names: list[str]) -> str:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=30)
    system = _SYSTEM + ("\nKEEP: " + "; ".join(keep_names) if keep_names else "\nKEEP: (none)")
    resp = _client.messages.create(
        model=config.FAST_MODEL,
        max_tokens=max(512, len(text) // 2 + 256),
        system=system,
        messages=[{"role": "user", "content": text}],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    out = json.loads(next(b.text for b in resp.content if b.type == "text"))["text"]
    if not isinstance(out, str) or not out.strip():
        raise ValueError("empty scrub result")
    return out


def scrub(text: str, keep_names: list[str] | None = None) -> str:
    """Regex pass, then Haiku. If Haiku fails, the regex-only text is returned."""
    cleaned = scrub_regex(text)
    if not cleaned.strip() or not config.ANTHROPIC_API_KEY:
        return cleaned
    try:
        return _haiku(cleaned, keep_names or [])
    except Exception:
        log.exception("Haiku scrub failed; storing regex-only text")
        return cleaned


# --- the hook --------------------------------------------------------------------
def _store(center_slug, session, conversation_id, question, answer, found, sources, model,
           usage, latency_ms, rewritten_query) -> None:
    try:
        with db.connect() as conn:
            keep = [r["name"] for r in db.rows(
                conn, "SELECT name FROM contacts WHERE center_slug = ?", (center_slug,))]
        q = scrub(question, keep)
        a = scrub(answer, keep)
        rq = scrub(rewritten_query, keep) if rewritten_query else None
        usage = usage or {}
        with db.connect() as conn:
            conn.execute(
                """INSERT INTO qa_log (center_slug, session_id, conversation_id, role, question,
                   rewritten_query, answer, found, sources_json, model, input_tokens,
                   output_tokens, cache_read_tokens, cache_write_tokens, latency_ms)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (center_slug, (session or {}).get("id"), conversation_id,
                 (session or {}).get("role"), q, rq, a, 1 if found else 0,
                 json.dumps(list(sources or [])), model, usage.get("input_tokens"),
                 usage.get("output_tokens"), usage.get("cache_read_tokens"),
                 usage.get("cache_write_tokens"), latency_ms),
            )
    except Exception:
        log.exception("log_turn failed")


def log_turn(
    *,
    center_slug: str,
    session: dict,
    conversation_id: str | None,
    question: str,
    answer: str,
    found: bool,
    sources: list[str],
    model: str | None,
    usage: dict,  # {input_tokens, output_tokens, cache_read_tokens, cache_write_tokens}
    latency_ms: int,
    rewritten_query: str | None = None,
) -> None:
    try:
        _pool.submit(_store, center_slug, session, conversation_id, question, answer, found,
                     sources, model, usage, latency_ms, rewritten_query)
    except Exception:
        log.exception("could not queue log_turn")
