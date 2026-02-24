from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: Optional[str]
    base_url: Optional[str]
