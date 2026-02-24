import re


def canonicalize_entity(name: str) -> str:
    normalized = re.sub(r"\s+", " ", name.strip())
    return normalized.title()
