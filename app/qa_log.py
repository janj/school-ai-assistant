"""Q/A logging with PII scrubbing. STUB: Track E implements.

Contract (docs/CONTRACTS.md §5): Track B calls log_turn() once per answered request.
It must never raise into the request path and must never store raw text or IPs.
"""


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
    return None
