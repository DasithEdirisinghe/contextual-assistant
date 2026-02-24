from enum import Enum


class CardType(str, Enum):
    TASK = "task"
    REMINDER = "reminder"
    IDEA_NOTE = "idea_note"
