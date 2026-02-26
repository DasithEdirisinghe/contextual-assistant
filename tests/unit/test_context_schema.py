from assistant.schemas.context import ContextUpdateOutput


def test_context_update_output_schema_validation() -> None:
    payload = {
        "context": {
            "people": [{"name": "Sarah", "strength": 0.9, "evidence_card_ids": [1], "last_seen_at": None}],
            "organizations": [],
            "projects": [],
            "themes": [],
            "important_upcoming": [{"card_id": 1, "title": "Call Sarah", "reason": "due soon"}],
            "miscellaneous": [],
        },
        "focus_summary": "Working on budget planning with Sarah.",
    }
    parsed = ContextUpdateOutput.model_validate(payload)
    assert parsed.context.people[0].name == "Sarah"
    assert parsed.focus_summary
