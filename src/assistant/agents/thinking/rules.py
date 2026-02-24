from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha1

from assistant.db.models import CardORM, EnvelopeORM


@dataclass
class SuggestionCandidate:
    suggestion_type: str
    title: str
    message: str
    priority: str
    score: float
    related_refs: dict
    fingerprint: str


def _fingerprint(value: str) -> str:
    return sha1(value.encode("utf-8")).hexdigest()


def detect_conflicts(cards: list[CardORM]) -> list[SuggestionCandidate]:
    grouped: dict[tuple[str, str], list[CardORM]] = defaultdict(list)
    for card in cards:
        if card.card_type != "task" or not card.assignee_text or not card.due_at:
            continue
        key = (card.assignee_text.strip().lower(), card.due_at.date().isoformat())
        grouped[key].append(card)

    out: list[SuggestionCandidate] = []
    for (assignee_key, due_date), group in grouped.items():
        if len(group) < 2:
            continue
        card_ids = sorted(card.id for card in group)
        assignee = group[0].assignee_text or assignee_key
        message = f"{assignee} has {len(group)} tasks due on {due_date}: " + "; ".join(
            f"#{c.id} {c.description}" for c in group
        )
        out.append(
            SuggestionCandidate(
                suggestion_type="conflict",
                title=f"Deadline Conflict for {assignee}",
                message=message,
                priority="high",
                score=min(1.0, 0.6 + 0.1 * len(group)),
                related_refs={"card_ids": card_ids, "assignee": assignee, "due_date": due_date},
                fingerprint=_fingerprint(f"conflict:{assignee_key}:{due_date}:{','.join(map(str, card_ids))}"),
            )
        )
    return out


def detect_next_steps(envelopes: list[EnvelopeORM]) -> list[SuggestionCandidate]:
    out: list[SuggestionCandidate] = []
    for envelope in envelopes:
        tasks = [c for c in envelope.cards if c.card_type == "task"]
        if not tasks:
            continue

        # Prefer earliest due task; fallback to oldest created task.
        due_tasks = [t for t in tasks if t.due_at is not None]
        if due_tasks:
            candidate = sorted(due_tasks, key=lambda x: x.due_at)[0]
        else:
            candidate = sorted(tasks, key=lambda x: x.created_at)[0]

        out.append(
            SuggestionCandidate(
                suggestion_type="next_step",
                title=f"Next Step in {envelope.name}",
                message=f"Prioritize task #{candidate.id}: {candidate.description}",
                priority="medium",
                score=0.7,
                related_refs={"envelope_id": envelope.id, "card_id": candidate.id},
                fingerprint=_fingerprint(f"next_step:{envelope.id}:{candidate.id}"),
            )
        )
    return out


def detect_recommendations(envelopes: list[EnvelopeORM], min_ideas: int = 3) -> list[SuggestionCandidate]:
    out: list[SuggestionCandidate] = []
    for envelope in envelopes:
        ideas = [c for c in envelope.cards if c.card_type == "idea_note"]
        if len(ideas) < min_ideas:
            continue
        idea_ids = sorted(c.id for c in ideas)
        out.append(
            SuggestionCandidate(
                suggestion_type="recommendation",
                title=f"Consolidate Ideas in {envelope.name}",
                message=f"You have {len(ideas)} ideas in this envelope. Consider creating an execution plan.",
                priority="medium",
                score=0.65,
                related_refs={"envelope_id": envelope.id, "card_ids": idea_ids},
                fingerprint=_fingerprint(f"recommendation:{envelope.id}:ideas:{len(ideas)}"),
            )
        )
    return out


def build_thinking_candidates(cards: list[CardORM], envelopes: list[EnvelopeORM]) -> list[SuggestionCandidate]:
    candidates: list[SuggestionCandidate] = []
    candidates.extend(detect_conflicts(cards))
    candidates.extend(detect_next_steps(envelopes))
    candidates.extend(detect_recommendations(envelopes))
    return candidates
