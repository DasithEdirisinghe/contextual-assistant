import json
from pathlib import Path

from assistant.agents.ingestion.fallback import FallbackExtractor


def main() -> None:
    fixture = Path("tests/fixtures/notes_golden_dataset.json")
    rows = json.loads(fixture.read_text(encoding="utf-8"))
    extractor = FallbackExtractor()

    total = len(rows)
    correct_type = 0
    assignee_hits = 0
    assignee_total = 0

    for row in rows:
        card = extractor.extract(row["note"])
        if card.card_type.value == row["expected_card_type"]:
            correct_type += 1

        expected_entities = {e.lower() for e in row.get("expected_entities", [])}
        expected_assignee = next(iter(expected_entities), None)
        if expected_assignee is not None:
            assignee_total += 1
            if (card.assignee or "").lower() == expected_assignee:
                assignee_hits += 1

    card_type_acc = (correct_type / total) if total else 0.0
    assignee_recall = (assignee_hits / assignee_total) if assignee_total else 1.0

    summary = {
        "samples": total,
        "card_type_accuracy": round(card_type_acc, 4),
        "assignee_recall": round(assignee_recall, 4),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
