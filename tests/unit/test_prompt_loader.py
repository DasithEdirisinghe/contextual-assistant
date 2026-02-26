from pathlib import Path

import pytest
import yaml

from assistant.prompts import file_sha256, load_prompt, load_prompt_versioned, load_registry, resolve_prompt_version
from assistant.prompts import loader as prompt_loader


def test_load_prompt_renders_variable() -> None:
    rendered = load_prompt("ingestion.jinja", raw_note="Call Sarah")
    assert "Call Sarah" in rendered


def test_load_prompt_missing_variable_raises() -> None:
    with pytest.raises(ValueError):
        load_prompt("ingestion.jinja")


def test_ingestion_prompt_contract_sections_exist() -> None:
    rendered = load_prompt("ingestion.jinja", raw_note="Call Sarah about the Q3 budget next Monday")
    lower = rendered.lower()
    assert "[role]" in lower
    assert "output contract" in lower
    assert "reasoning_steps" in lower
    assert "confidence" in lower
    assert "assignee" in lower
    assert "date_text" in lower


def test_load_prompt_versioned_uses_current_when_version_missing() -> None:
    rendered = load_prompt_versioned("ingestion", raw_note="Call Sarah")
    assert "Call Sarah" in rendered
    assert "[role]" in rendered.lower()


def test_load_prompt_versioned_specific_snapshot() -> None:
    rendered = load_prompt_versioned("ingestion", version="ingestion.extract.v1", raw_note="Call Sarah")
    assert "information extraction assistant" in rendered


def test_prompt_registry_integrity() -> None:
    registry = load_registry("ingestion")
    assert registry["prompt_id"] == "ingestion"
    assert registry["current_template"]
    versions = registry["versions"]
    assert any(v["version"] == registry["current_version"] for v in versions)
    for version in versions:
        template_file = Path("src/assistant/prompts") / version["template_file"]
        assert template_file.exists()


def test_prompt_version_consistency() -> None:
    registry = load_registry("ingestion")
    assert resolve_prompt_version("ingestion") == registry["current_version"]


def test_current_alias_matches_current_template_snapshot() -> None:
    registry = load_registry("ingestion")
    prompts_dir = Path("src/assistant/prompts")
    alias = (prompts_dir / "ingestion.jinja").read_text(encoding="utf-8")
    current = (prompts_dir / registry["current_template"]).read_text(encoding="utf-8")
    assert alias == current


def test_snapshot_immutability_guard_with_sha256() -> None:
    registry = load_registry("ingestion")
    prompts_dir = Path("src/assistant/prompts")
    for version in registry["versions"]:
        template = prompts_dir / version["template_file"]
        assert file_sha256(template) == version["sha256"]


def test_resolve_prompt_version_with_explicit_valid_version() -> None:
    assert resolve_prompt_version("ingestion", "ingestion.extract.v7") == "ingestion.extract.v7"


def test_resolve_prompt_version_invalid_raises() -> None:
    with pytest.raises(ValueError, match="Unknown prompt version"):
        resolve_prompt_version("ingestion", "ingestion.extract.v999")


def test_resolve_prompt_version_missing_template_file_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True)
    registry_path = prompts_dir / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "prompt_id": "ingestion",
                "current_version": "ingestion.extract.v1",
                "current_template": "ingestion.v1.jinja",
                "schema_version": "ingestion.schema.v4",
                "versions": [
                    {
                        "version": "ingestion.extract.v1",
                        "template_file": "missing-file.jinja",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(prompt_loader, "PROMPTS_DIR", prompts_dir)
    monkeypatch.setattr(prompt_loader, "REGISTRY_PATH", registry_path)

    with pytest.raises(FileNotFoundError, match="not found for version"):
        resolve_prompt_version("ingestion", "ingestion.extract.v1")
