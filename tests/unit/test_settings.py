from assistant.config.settings import Settings


def test_settings_ingestion_prompt_version_default_none() -> None:
    settings = Settings(_env_file=None)
    assert settings.ingestion_prompt_version is None


def test_settings_ingestion_prompt_version_loads_from_alias() -> None:
    settings = Settings(INGESTION_PROMPT_VERSION="ingestion.extract.v7")
    assert settings.ingestion_prompt_version == "ingestion.extract.v7"
