from __future__ import annotations

from datetime import datetime

import dateparser


def parse_due_at(date_text: str | None, timezone: str = "UTC") -> datetime | None:
    if not date_text:
        return None
    return dateparser.parse(
        date_text,
        settings={
            "RETURN_AS_TIMEZONE_AWARE": False,
            "TIMEZONE": timezone,
            "PREFER_DATES_FROM": "future",
        },
    )
