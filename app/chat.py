"""Answer pipeline. STUB: Track B implements.

Contract (docs/CONTRACTS.md §3): answer(session, message, conversation_id) returns the
/api/chat response body. Raises limits.LimitExceeded for 429s, UpstreamError for 503s.
"""


class UpstreamError(Exception):
    pass


def answer(session: dict, message: str, conversation_id: str | None, client_ip: str) -> dict:
    return {
        "answer": f"(stub) You asked: {message}",
        "found": False,
        "sources": [],
        "contact": None,
        "conversation_id": conversation_id,
    }
