"""In-memory conversation history (Track G). Raw text lives here only, never in the database.

Keyed by (session_id, conversation_id), so one browser can't read another's thread by guessing
an id. Lost on restart by design.
"""

import os
import threading
import time
from collections import OrderedDict

SEND_TURNS = 4          # most recent turns given to the model
MAX_TURNS = 8           # hard cap per conversation
MAX_CONVERSATIONS = 2000
IDLE_SECONDS = int(os.environ.get("CONVERSATION_IDLE_SECONDS", 30 * 60))

TURN_CAP_DETAIL = "This conversation has reached its limit. Start a new one."


class TurnCapReached(Exception):
    detail = TURN_CAP_DETAIL
    kind = "turn_cap"


_lock = threading.Lock()
# key -> {"turns": [(question, answer, ts)], "last": ts}; ordered oldest-touched first
_store: "OrderedDict[tuple[str, str], dict]" = OrderedDict()


def _prune(now: float) -> None:
    for key in [k for k, v in _store.items() if now - v["last"] > IDLE_SECONDS]:
        del _store[key]
    while len(_store) > MAX_CONVERSATIONS:
        _store.popitem(last=False)


def recent(session_id: str, conversation_id: str | None) -> list[tuple[str, str]]:
    """Last SEND_TURNS (question, answer) pairs. Raises TurnCapReached when the thread is full."""
    if not conversation_id:
        return []
    now = time.time()
    with _lock:
        _prune(now)
        conv = _store.get((session_id, conversation_id))
        if not conv:
            return []
        if len(conv["turns"]) >= MAX_TURNS:
            raise TurnCapReached()
        return [(q, a) for q, a, _ in conv["turns"][-SEND_TURNS:]]


def add_turn(session_id: str, conversation_id: str | None, question: str, answer: str) -> None:
    if not conversation_id:
        return
    now = time.time()
    key = (session_id, conversation_id)
    with _lock:
        _prune(now)
        conv = _store.setdefault(key, {"turns": [], "last": now})
        conv["turns"].append((question, answer, now))
        conv["last"] = now
        _store.move_to_end(key)
