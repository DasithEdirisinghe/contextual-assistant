from assistant.ml.extraction.fallback import FallbackExtractor


extractor = FallbackExtractor()


def test_fallback_task_classification() -> None:
    card = extractor.extract("Call Sarah about the Q3 budget next Monday")
    assert card.card_type in {"task", "reminder"}
    assert "sarah" in (card.assignee or "").lower()


def test_fallback_idea_classification() -> None:
    card = extractor.extract("Idea: new logo should be blue and green")
    assert card.card_type == "idea_note"
