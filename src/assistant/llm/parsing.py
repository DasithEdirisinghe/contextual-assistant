from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def extract_json_block(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def parse_structured_content(content: object, schema_cls: type[ModelT]) -> ModelT:
    if isinstance(content, str):
        raw = content
    else:
        raw = json.dumps(content)

    try:
        return schema_cls.model_validate_json(raw)
    except Exception:
        cleaned = extract_json_block(raw)
        return schema_cls.model_validate_json(cleaned)
