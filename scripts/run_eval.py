import json
from pathlib import Path

from assistant.agents.ingestion.fallback import FallbackExtractor


def main() -> None:
    fixture = Path("tests/fixtures/notes_golden_dataset.json")
    rows = json.loads(fixture.read_text(encoding="utf-8"))
    extractor = FallbackExtractor()

    total = len(rows)
    correct_type = 0
    entity_hits = 0
    entity_total = 0

    for row in rows:
        card = extractor.extract(row["note"])
        if card.card_type.value == row["expected_card_type"]:
            correct_type += 1

        expected_entities = {e.lower() for e in row.get("expected_entities", [])}
        predicted_entities = {e.value.lower() for e in card.entities}
        entity_hits += len(expected_entities.intersection(predicted_entities))
        entity_total += len(expected_entities)

    card_type_acc = (correct_type / total) if total else 0.0
    entity_recall = (entity_hits / entity_total) if entity_total else 1.0

    summary = {
        "samples": total,
        "card_type_accuracy": round(card_type_acc, 4),
        "entity_recall": round(entity_recall, 4),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
