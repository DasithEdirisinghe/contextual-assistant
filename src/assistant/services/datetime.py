from __future__ import annotations

from datetime import datetime

import dateparser
from dateparser.search import search_dates


def parse_due_at(date_text: str | None, timezone: str = "UTC") -> datetime | None:
    if not date_text:
        return None
    settings = {
        "RETURN_AS_TIMEZONE_AWARE": False,
        "TIMEZONE": timezone,
        "PREFER_DATES_FROM": "future",
    }

    parsed = dateparser.parse(
        date_text,
        settings=settings,
    )
    if parsed is not None:
        return parsed

    # Fallback for phrases parse() misses, such as "next Monday".
    matches = search_dates(date_text, settings=settings)
    if not matches:
        return None
    return matches[0][1]
