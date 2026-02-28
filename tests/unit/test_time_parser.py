from assistant.services.datetime import parse_due_at


def test_parse_due_at_relative_date() -> None:
    parsed = parse_due_at("tomorrow")
    assert parsed is not None


def test_parse_due_at_next_monday_phrase() -> None:
    parsed = parse_due_at("next Monday")
    assert parsed is not None
