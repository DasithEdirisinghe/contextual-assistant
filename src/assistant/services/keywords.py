from __future__ import annotations

import re


def extract_keywords(text: str, limit: int = 6) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text)
    lowered = [t.lower() for t in tokens]
    return sorted(set(lowered[:limit]))
