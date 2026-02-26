from __future__ import annotations

import argparse
import hashlib
import re
from datetime import date
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "src" / "assistant" / "prompts"
REGISTRY_PATH = PROMPTS_DIR / "registry.yaml"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_version(version: str, prompt_id: str) -> int:
    pattern = rf"{re.escape(prompt_id)}(?:\.[a-z_]+)?\.v(\d+)"
    match = re.fullmatch(pattern, version.strip())
    if not match:
        raise ValueError(f"Unsupported version format for prompt_id '{prompt_id}': {version}")
    return int(match.group(1))


def _next_version(current_version: str, prompt_id: str) -> tuple[str, str]:
    current_n = _parse_version(current_version, prompt_id)
    next_n = current_n + 1
    if ".extract." in current_version:
        version = f"{prompt_id}.extract.v{next_n}"
    else:
        version = f"{prompt_id}.v{next_n}"
    template = f"{prompt_id}.v{next_n}.jinja"
    return version, template


def main() -> None:
    parser = argparse.ArgumentParser(description="Release immutable prompt snapshot for a prompt_id.")
    parser.add_argument("--prompt-id", required=True, help="Prompt id in registry.yaml prompts map.")
    parser.add_argument("--source-template", default=None, help="Template filename to release. Defaults to <prompt_id>.jinja")
    parser.add_argument("--owner", default="mle-team", help="Owner metadata for registry entry.")
    parser.add_argument("--changelog", required=True, help="One-line changelog for this prompt release.")
    parser.add_argument("--schema-version", default=None, help="Optional schema version override for this prompt.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    args = parser.parse_args()

    source_template = args.source_template or f"{args.prompt_id}.jinja"
    source_path = PROMPTS_DIR / source_template
    if not source_path.exists():
        raise FileNotFoundError(f"Source template not found: {source_path}")

    registry = yaml.safe_load(_read_text(REGISTRY_PATH))
    if not isinstance(registry, dict):
        raise ValueError("Invalid registry format")
    prompts = registry.get("prompts")
    if not isinstance(prompts, dict):
        raise ValueError("Registry missing prompts map")
    block = prompts.get(args.prompt_id)
    if not isinstance(block, dict):
        raise ValueError(f"Unknown prompt_id: {args.prompt_id}")

    current_version = block.get("current_version")
    current_template = block.get("current_template")
    versions = block.get("versions")
    if not current_version or not current_template or not isinstance(versions, list):
        raise ValueError(f"Registry block malformed for prompt_id: {args.prompt_id}")

    next_version, next_template = _next_version(current_version, args.prompt_id)
    next_template_path = PROMPTS_DIR / next_template
    alias_path = PROMPTS_DIR / f"{args.prompt_id}.jinja"

    if next_template_path.exists():
        raise FileExistsError(f"Target snapshot already exists: {next_template_path}")

    source_content = _read_text(source_path)
    planned_schema_version = args.schema_version or block.get("schema_version")
    if not planned_schema_version:
        raise ValueError("schema_version missing; pass --schema-version")

    if args.dry_run:
        print(f"[dry-run] prompt_id: {args.prompt_id}")
        print(f"[dry-run] source template: {source_path.name}")
        print(f"[dry-run] create snapshot: {next_template}")
        print(f"[dry-run] set current_version: {next_version}")
        print(f"[dry-run] set current_template: {next_template}")
        print(f"[dry-run] schema_version: {planned_schema_version}")
    else:
        _write_text(next_template_path, source_content)
        _write_text(alias_path, source_content)
        sha = _sha256(next_template_path)

        block["current_version"] = next_version
        block["current_template"] = next_template
        block["schema_version"] = planned_schema_version
        versions.append(
            {
                "version": next_version,
                "template_file": next_template,
                "created_at": date.today().isoformat(),
                "owner": args.owner,
                "changelog": args.changelog.strip(),
                "sha256": sha,
            }
        )
        _write_text(REGISTRY_PATH, yaml.safe_dump(registry, sort_keys=False))

    print(f"Released prompt: {next_version}")
    print(f"Snapshot file: {next_template}")
    print(f"Source template: {source_path.name}")
    if args.dry_run:
        print("No files were written (--dry-run).")
    else:
        print(f"Updated: {args.prompt_id}.jinja, registry.yaml")


if __name__ == "__main__":
    main()
