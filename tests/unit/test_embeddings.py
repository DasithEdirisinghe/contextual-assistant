from assistant.config.settings import Settings
from assistant.services import embeddings


def test_semantic_similarity_uses_lexical_fallback_when_model_unavailable() -> None:
    settings = Settings(EMBEDDING_PROVIDER="openai", EMBEDDING_API_KEY=None)
    score_related = embeddings.semantic_similarity("q3 budget planning", "budget planning for q3", settings=settings)
    score_unrelated = embeddings.semantic_similarity("q3 budget planning", "buy milk tonight", settings=settings)
    assert score_related > score_unrelated


def test_semantic_similarity_uses_model_vectors_when_available(monkeypatch) -> None:
    settings = Settings(EMBEDDING_PROVIDER="openai", EMBEDDING_API_KEY="dummy")

    def fake_embed(provider: str, model: str, api_key: str, base_url: str, text: str):
        if "budget" in text:
            return (1.0, 0.0)
        return (0.0, 1.0)

    monkeypatch.setattr(embeddings, "_embed_text_model", fake_embed)

    same_topic = embeddings.semantic_similarity("budget q3", "budget forecast", settings=settings)
    different_topic = embeddings.semantic_similarity("budget q3", "grocery eggs", settings=settings)
    assert same_topic > different_topic
