from __future__ import annotations

import json


def pretty_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, default=str)
