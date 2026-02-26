from __future__ import annotations

import logging
import math
import re
from collections import Counter
from functools import lru_cache
from typing import Sequence

from openai import OpenAI

from assistant.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

MODEL_PROVIDERS = {"openai", "openai_compatible", "deepseek", "ollama"}
_MODEL_FAILURE_CACHE: set[tuple[str, str, str, str]] = set()


def embed(text: str) -> Counter:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return Counter(tokens)


def _cosine_sparse(vec_a: Counter, vec_b: Counter) -> float:
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(vec_a[t] * vec_b[t] for t in set(vec_a).intersection(vec_b))
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _cosine_dense(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def similarity(vec_a: Counter | Sequence[float], vec_b: Counter | Sequence[float]) -> float:
    if isinstance(vec_a, Counter) and isinstance(vec_b, Counter):
        return _cosine_sparse(vec_a, vec_b)
    if isinstance(vec_a, Sequence) and isinstance(vec_b, Sequence):
        try:
            return _cosine_dense([float(v) for v in vec_a], [float(v) for v in vec_b])
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _resolve_provider(settings: Settings) -> str:
    provider = settings.effective_embedding_provider
    if provider != "auto":
        return provider
    llm_provider = settings.effective_llm_provider
    return llm_provider if llm_provider in MODEL_PROVIDERS else "lexical"


def _resolve_endpoint(provider: str, settings: Settings) -> str:
    base_url = settings.effective_embedding_base_url
    if base_url:
        return base_url
    if provider == "deepseek":
        return "https://api.deepseek.com/v1"
    if provider == "ollama":
        return "http://localhost:11434/v1"
    return ""


def _should_use_model(provider: str, settings: Settings) -> bool:
    if provider not in MODEL_PROVIDERS:
        return False
    if not settings.effective_embedding_model:
        return False
    if provider in {"openai", "deepseek", "openai_compatible"} and not settings.effective_embedding_api_key:
        return False
    if provider == "openai_compatible" and not _resolve_endpoint(provider, settings):
        return False
    return True


@lru_cache(maxsize=8)
def _build_client(api_key: str, base_url: str) -> OpenAI:
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


@lru_cache(maxsize=2048)
def _embed_text_model(provider: str, model: str, api_key: str, base_url: str, text: str) -> tuple[float, ...]:
    failure_key = (provider, model, api_key[:8], base_url)
    if failure_key in _MODEL_FAILURE_CACHE:
        return tuple()
    try:
        client = _build_client(api_key=api_key, base_url=base_url)
        response = client.embeddings.create(model=model, input=text)
        return tuple(response.data[0].embedding)
    except Exception:
        logger.warning("Model embedding failed; falling back to lexical similarity", exc_info=True)
        _MODEL_FAILURE_CACHE.add(failure_key)
        return tuple()


def semantic_similarity(text_a: str, text_b: str, settings: Settings | None = None) -> float:
    runtime_settings = settings or get_settings()
    provider = _resolve_provider(runtime_settings)
    if _should_use_model(provider, runtime_settings):
        vec_a = model_embed(text_a, settings=runtime_settings)
        vec_b = model_embed(text_b, settings=runtime_settings)
        if vec_a and vec_b:
            return similarity(vec_a, vec_b)
    return similarity(embed(text_a), embed(text_b))


def model_embed(text: str, settings: Settings | None = None) -> list[float]:
    runtime_settings = settings or get_settings()
    provider = _resolve_provider(runtime_settings)
    if not _should_use_model(provider, runtime_settings):
        return []
    model = runtime_settings.effective_embedding_model
    api_key = runtime_settings.effective_embedding_api_key or "unused"
    base_url = _resolve_endpoint(provider, runtime_settings)
    vec = _embed_text_model(provider, model, api_key, base_url, text)
    return [float(v) for v in vec] if vec else []
