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


def _parse_version(version: str) -> int:
    match = re.fullmatch(r"ingestion\.extract\.v(\d+)", version.strip())
    if not match:
        raise ValueError(f"Unsupported version format: {version}")
    return int(match.group(1))


def _next_version(current_version: str) -> tuple[str, str]:
    current_n = _parse_version(current_version)
    next_n = current_n + 1
    return f"ingestion.extract.v{next_n}", f"ingestion.v{next_n}.jinja"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a new immutable ingestion prompt version and update registry/alias."
    )
    parser.add_argument(
        "--source-template",
        default="ingestion.jinja",
        help="Template file under src/assistant/prompts to release (default: ingestion.jinja).",
    )
    parser.add_argument(
        "--owner",
        default="mle-team",
        help="Owner metadata for registry entry.",
    )
    parser.add_argument(
        "--changelog",
        required=True,
        help="One-line changelog for this prompt release.",
    )
    parser.add_argument(
        "--schema-version",
        default=None,
        help="Optional schema version override (defaults to existing registry schema_version).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing files.",
    )
    args = parser.parse_args()

    source_path = PROMPTS_DIR / args.source_template
    if not source_path.exists():
        raise FileNotFoundError(f"Source template not found: {source_path}")

    registry = yaml.safe_load(_read_text(REGISTRY_PATH))
    if not isinstance(registry, dict):
        raise ValueError("Invalid registry format")

    prompt_id = registry.get("prompt_id")
    if prompt_id != "ingestion":
        raise ValueError(f"Unexpected prompt_id in registry: {prompt_id}")

    current_version = registry.get("current_version")
    current_template = registry.get("current_template")
    versions = registry.get("versions")
    if not current_version or not current_template or not isinstance(versions, list):
        raise ValueError("Registry missing required fields")

    next_version, next_template = _next_version(current_version)
    next_template_path = PROMPTS_DIR / next_template
    alias_path = PROMPTS_DIR / "ingestion.jinja"

    if next_template_path.exists():
        raise FileExistsError(f"Target snapshot already exists: {next_template_path}")

    source_content = _read_text(source_path)
    planned_schema_version = args.schema_version or registry.get("schema_version")
    if not planned_schema_version:
        raise ValueError("schema_version missing in registry; pass --schema-version")

    if args.dry_run:
        print(f"[dry-run] source template: {source_path.name}")
        print(f"[dry-run] create snapshot: {next_template}")
        print(f"[dry-run] set current_version: {next_version}")
        print(f"[dry-run] set current_template: {next_template}")
        print(f"[dry-run] schema_version: {planned_schema_version}")
    else:
        _write_text(next_template_path, source_content)
        _write_text(alias_path, source_content)
        sha = _sha256(next_template_path)

        registry["current_version"] = next_version
        registry["current_template"] = next_template
        registry["schema_version"] = planned_schema_version
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
        print("Updated: ingestion.jinja, registry.yaml")


if __name__ == "__main__":
    main()
