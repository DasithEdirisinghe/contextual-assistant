from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROMPTS_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = PROMPTS_DIR / "registry.yaml"


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


def load_registry(prompt_id: str = "ingestion") -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Prompt registry not found: {REGISTRY_PATH}")
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    # Backward-compatible read: old single-prompt registry shape.
    if "prompts" not in data:
        if data.get("prompt_id") != prompt_id:
            raise ValueError(f"Registry prompt_id mismatch: expected '{prompt_id}', found '{data.get('prompt_id')}'")
        return data

    prompts = data.get("prompts")
    if not isinstance(prompts, dict):
        raise ValueError("Registry malformed: 'prompts' must be a mapping")
    prompt_block = prompts.get(prompt_id)
    if not isinstance(prompt_block, dict):
        raise ValueError(f"Unknown prompt_id '{prompt_id}' in registry")
    # Normalize to per-prompt shape expected by existing helpers.
    normalized = {"prompt_id": prompt_id, **prompt_block}
    return normalized


def resolve_prompt_version(prompt_id: str, requested_version: str | None = None) -> str:
    registry = load_registry(prompt_id=prompt_id)
    versions = registry.get("versions")
    if not isinstance(versions, list):
        raise ValueError(f"Registry malformed for prompt_id '{prompt_id}': 'versions' must be a list")

    if requested_version is None or not str(requested_version).strip():
        current_version = registry.get("current_version")
        if not isinstance(current_version, str) or not current_version.strip():
            raise ValueError(f"Registry malformed for prompt_id '{prompt_id}': missing current_version")
        requested_version = current_version

    match = next((entry for entry in versions if entry.get("version") == requested_version), None)
    if not match:
        raise ValueError(
            f"Unknown prompt version '{requested_version}' for prompt_id '{prompt_id}'. "
            "Add it to registry.yaml versions[] first."
        )

    template_name = match.get("template_file")
    if not isinstance(template_name, str) or not template_name.strip():
        raise ValueError(
            f"Registry malformed for prompt_id '{prompt_id}': version '{requested_version}' missing template_file"
        )

    path = PROMPTS_DIR / template_name
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt template file '{template_name}' not found for version '{requested_version}' (prompt_id '{prompt_id}')"
        )
    return str(requested_version)


def load_prompt_versioned(prompt_id: str, version: str | None = None, **kwargs: object) -> str:
    registry = load_registry(prompt_id=prompt_id)
    versions = registry.get("versions", [])
    resolved_version = resolve_prompt_version(prompt_id=prompt_id, requested_version=version)
    match = next((entry for entry in versions if entry.get("version") == resolved_version), None)
    if not match:
        raise ValueError(f"Version '{resolved_version}' not found for prompt_id '{prompt_id}'")
    template_name = match.get("template_file")
    if not template_name:
        raise ValueError(f"Version '{resolved_version}' missing template_file")
    return load_prompt(str(template_name), **kwargs)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
