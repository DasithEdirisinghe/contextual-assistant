from assistant.agents.ingestion.fallback import FallbackExtractor


extractor = FallbackExtractor()


def test_fallback_task_classification() -> None:
    card = extractor.extract("Call Sarah about the Q3 budget next Monday")
    assert card.card_type in {"task", "reminder"}
    assert "sarah" in (card.assignee or "").lower()


def test_fallback_idea_classification() -> None:
    card = extractor.extract("Idea: new logo should be blue and green")
    assert card.card_type == "idea_note"


def test_fallback_regression_expected_card_fields() -> None:
    card = extractor.extract("Call Sarah about the Q3 budget next Monday")
    assert card.card_type == "task"
    assert card.assignee == "Sarah"
    assert card.date_text == "next monday"
    assert card.confidence >= 0.55


def test_fallback_regression_reminder_has_no_invented_assignee() -> None:
    card = extractor.extract("Remember to pick up milk on the way home")
    assert card.card_type == "reminder"
    assert card.assignee is None


def test_fallback_regression_idea_has_no_due_date() -> None:
    card = extractor.extract("Idea: new logo should be blue and green")
    assert card.card_type == "idea_note"
    assert card.date_text is None
