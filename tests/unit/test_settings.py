from assistant.config.settings import Settings


def test_settings_ingestion_prompt_version_default_none() -> None:
    settings = Settings(_env_file=None)
    assert settings.ingestion_prompt_version is None


def test_settings_ingestion_prompt_version_loads_from_alias() -> None:
    settings = Settings(INGESTION_PROMPT_VERSION="ingestion.extract.v7")
    assert settings.ingestion_prompt_version == "ingestion.extract.v7"


def test_settings_other_prompt_versions_load_from_aliases() -> None:
    settings = Settings(
        ENVELOPE_REFINE_PROMPT_VERSION="envelope_refine.v1",
        CONTEXT_UPDATE_PROMPT_VERSION="context_update.v1",
        THINKING_PROMPT_VERSION="thinking.v1",
    )
    assert settings.envelope_refine_prompt_version == "envelope_refine.v1"
    assert settings.context_update_prompt_version == "context_update.v1"
    assert settings.thinking_prompt_version == "thinking.v1"
