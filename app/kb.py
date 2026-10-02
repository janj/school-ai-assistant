"""Renders one center's knowledge base into prompt text. STUB: Track B implements.

Contract (docs/CONTRACTS.md §4): every section starts with a line `[section: <id>]`.
Section IDs: center, contacts, hours, closures, schedule, fees, lunch_menu,
policy:<topic>, faq:<id>. section_ids() returns exactly the IDs present.
"""


def render_center_kb(center_slug: str) -> str:
    return f"[section: center]\nPlaceholder knowledge base for {center_slug}."


def section_ids(center_slug: str) -> set[str]:
    return {"center"}
