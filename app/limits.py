"""Per-IP request-count limit and token budget. STUB: Track B implements.

IPs are held only in process memory (never logged or persisted). Single uvicorn
worker, so in-memory state is the whole truth.
"""


class LimitExceeded(Exception):
    def __init__(self, kind: str, detail: str):  # kind: "rate" | "budget"
        super().__init__(detail)
        self.kind = kind
        self.detail = detail
