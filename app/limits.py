"""Per-IP request-count limit and token budget.

IPs are held only in process memory (never logged or persisted). Single uvicorn
worker, so in-memory state is the whole truth.
"""

import threading
import time
from collections import deque

from app import config

DAY_S = 86_400


class LimitExceeded(Exception):
    def __init__(self, kind: str, detail: str):  # kind: "rate" | "budget"
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


_lock = threading.Lock()
_requests: dict[str, deque] = {}   # ip -> request timestamps
_tokens: dict[str, deque] = {}     # ip -> (timestamp, weighted tokens), kept for 24h


def _prune(dq: deque, cutoff: float) -> None:
    while dq and (dq[0][0] if isinstance(dq[0], tuple) else dq[0]) < cutoff:
        dq.popleft()


def _wait(seconds: float) -> str:
    mins = max(1, round(seconds / 60))
    if mins >= 90:
        hours = round(mins / 60)
        return f"about {hours} hours"
    return f"about {mins} minute{'s' if mins != 1 else ''}"


def check(ip: str) -> None:
    now = time.time()
    with _lock:
        reqs = _requests.setdefault(ip, deque())
        _prune(reqs, now - config.RATE_LIMIT_WINDOW_S)
        toks = _tokens.setdefault(ip, deque())
        _prune(toks, now - DAY_S)
        if not reqs and not toks:  # keep the dicts bounded
            _requests.pop(ip, None)
            _tokens.pop(ip, None)

        if len(reqs) >= config.RATE_LIMIT_REQUESTS:
            wait = reqs[0] + config.RATE_LIMIT_WINDOW_S - now
            raise LimitExceeded("rate", f"You're asking questions quickly. Please try again in {_wait(wait)}.")

        short_cut = now - config.TOKEN_BUDGET_SHORT_WINDOW_S
        short_used = sum(t for ts, t in toks if ts >= short_cut)
        if short_used >= config.TOKEN_BUDGET_SHORT:
            first = next(ts for ts, _ in toks if ts >= short_cut)
            wait = first + config.TOKEN_BUDGET_SHORT_WINDOW_S - now
            raise LimitExceeded("budget", f"You've reached the usage limit for now. Please try again in {_wait(wait)}.")

        if sum(t for _, t in toks) >= config.TOKEN_BUDGET_DAILY:
            wait = toks[0][0] + DAY_S - now
            raise LimitExceeded("budget", f"You've reached today's usage limit. Please try again in {_wait(wait)}.")

        reqs.append(now)  # counted at check time so concurrent bursts can't slip through


def record(ip: str, tokens: float) -> None:
    """tokens = input + output + cache-creation + 0.1 * cache-read (caller weights it)."""
    with _lock:
        _tokens.setdefault(ip, deque()).append((time.time(), tokens))
