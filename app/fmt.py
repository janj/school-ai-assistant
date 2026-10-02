"""Value formatting shared by the KB renderer and placeholder resolution."""

from datetime import date, datetime


def time(value: str | None) -> str:
    """'18:00' -> '6:00 PM'."""
    if not value:
        return ""
    return datetime.strptime(value, "%H:%M").strftime("%I:%M %p").lstrip("0")


def money(cents: int | None) -> str:
    if cents is None:
        return ""
    return f"-${-cents / 100:,.2f}" if cents < 0 else f"${cents / 100:,.2f}"


def day(value: str) -> str:
    d = date.fromisoformat(value)
    return f"{d.strftime('%A %B')} {d.day}, {d.year}"


def span(start: str | None, end: str | None) -> str:
    if start and end:
        return f"{time(start)} - {time(end)}"
    return time(start) or time(end)
