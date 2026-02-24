from assistant.ml.normalization.time_parser import parse_due_at


def test_parse_due_at_relative_date() -> None:
    parsed = parse_due_at("tomorrow")
    assert parsed is not None
