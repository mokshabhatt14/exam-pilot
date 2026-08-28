"""
knowledge_state.py

Defines the data model for a single topic's knowledge state inside a
student's Knowledge Twin. This is the "memory" layer — the Knowledge Twin
Engine reads and writes to these objects, but the forgetting math lives
in forgetting_model.py.

Design notes for the team:
- confidence: 0-100. "How well the student currently knows this topic,
  at the moment it was last updated." This is NOT auto-decayed here —
  decay is applied on read, via the engine, so the stored value always
  represents "confidence as of last_updated".
- stability: a spaced-repetition-style number (in days). Roughly:
  "how many days it takes for confidence to decay meaningfully if the
  student does nothing." Higher stability = the student has a firmer
  grip on the topic and forgets it more slowly.
- exam_date: optional calendar date of the exam/test this topic belongs
  to. Added for Person 4's Prediction + Adaptive Intelligence layer,
  which uses it to compute exam urgency. Left optional and defaulting to
  None so topics without a known exam date just get 0 urgency instead of
  breaking anything — Person 2's backend can populate this from the
  syllabus/exam schedule whenever it's ready.
- history: append-only log of every action taken on this topic. This is
  what makes the twin explainable — you can always answer "why does the
  twin believe this?" by pointing at concrete events.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class ActionEvent:
    """A single recorded action on a topic (one line of the audit trail)."""
    action_type: str            # "studied" | "quiz" | "revision" | "mistake" | "skipped"
    timestamp: datetime
    detail: str = ""            # human-readable note, e.g. "quiz score 58%"
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    stability_before: float = 0.0
    stability_after: float = 0.0


@dataclass
class TopicState:
    """Everything the twin currently believes about one topic."""
    topic: str
    confidence: float = 30.0        # starting assumption: mostly unknown
    stability: float = 3.0          # days; starts moderate, grows with good revisions
    last_updated: datetime = field(default_factory=datetime.now)
    exam_weight: float = 1.0        # relative importance of this topic (0-1+), set by syllabus
    exam_date: Optional[date] = None  # NEW: when this topic's exam falls; used by Person 4's urgency calc
    history: list = field(default_factory=list)  # list[ActionEvent]

    def log(self, event: ActionEvent) -> None:
        self.history.append(event)

    def to_dict(self) -> dict:
        """Serializable snapshot — this is the contract other modules
        (dashboard, planner, backend API) can rely on."""
        return {
            "topic": self.topic,
            "confidence": round(self.confidence, 1),
            "stability_days": round(self.stability, 2),
            "last_updated": self.last_updated.isoformat(),
            "exam_weight": self.exam_weight,
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
            "history_length": len(self.history),
        }
