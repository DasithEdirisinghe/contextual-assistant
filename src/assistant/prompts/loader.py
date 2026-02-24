from __future__ import annotations

import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(template_name: str, **kwargs: object) -> str:
    path = PROMPTS_DIR / template_name
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_name}")

    text = path.read_text(encoding="utf-8")

    def replace_var(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key not in kwargs:
            raise ValueError(f"Missing template variable '{key}' for {template_name}")
        value = kwargs[key]
        return "" if value is None else str(value)

    return re.sub(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", replace_var, text)
