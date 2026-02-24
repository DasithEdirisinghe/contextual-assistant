from __future__ import annotations

import math
import re
from collections import Counter


def embed(text: str) -> Counter:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return Counter(tokens)


def similarity(vec_a: Counter, vec_b: Counter) -> float:
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(vec_a[t] * vec_b[t] for t in set(vec_a).intersection(vec_b))
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_similarity(text_a: str, text_b: str) -> float:
    return similarity(embed(text_a), embed(text_b))
