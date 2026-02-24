import pytest

from assistant.prompts import load_prompt


def test_load_prompt_renders_variable() -> None:
    rendered = load_prompt("ingestion.jinja", raw_note="Call Sarah")
    assert "Call Sarah" in rendered


def test_load_prompt_missing_variable_raises() -> None:
    with pytest.raises(ValueError):
        load_prompt("ingestion.jinja")
