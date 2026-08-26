"""
prediction_engine.py

The decision-making layer on top of the Knowledge Twin. Turns raw
TopicKnowledgeState objects into:
  - exam urgency scores
  - topic priority scores (what should the student worry about most)
  - ranked recommendations with a human-readable "why" explanation
  - a mechanism for the student to disagree with the AI
  - a sanity-check evaluator over the engine's own output
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional

from knowledge_state import TopicKnowledgeState
from forgetting_model import compute_forgetting_risk, clamp


DEFAULT_WEIGHTS = {
    "forgetting_risk": 0.40,
    "exam_urgency": 0.30,
    "difficulty": 0.15,
    "mistake_density": 0.15,
}


@dataclass
class TopicRecommendation:
    topic_id: str
    topic_name: str
    subject: str
    forgetting_risk: float
    exam_urgency: float
    difficulty_score: float
    mistake_density: float
    priority_score: float
    explanation: str


@dataclass
class DisagreementEvent:
    topic_id: str
    student_claimed_confidence: float
    reason: str
    date_raised: date
    expires: date


class PredictionEngine:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        # Keep a log of disagreements for transparency / judge demo purposes.
        self.disagreement_log: List[DisagreementEvent] = []

    # ---------- Exam urgency ----------

    def exam_urgency(self, state: TopicKnowledgeState, as_of: date) -> float:
        """0-1 score, rising sharply as the exam date approaches.
        Uses an inverse curve rather than linear so the last few days
        before an exam dominate the ranking."""
        days_left = state.days_until_exam(as_of)
        if days_left <= 0:
            return 1.0
        # 1 day left -> ~0.91, 7 days -> ~0.55, 30 days -> ~0.20
        urgency = 10.0 / (10.0 + days_left)
        return round(clamp(urgency, 0.0, 1.0), 4)

    # ---------- Priority scoring ----------

    def difficulty_score(self, state: TopicKnowledgeState) -> float:
        # 1 (easy) -> 0.0, 5 (hard) -> 1.0
        return clamp((state.difficulty - 1) / 4.0, 0.0, 1.0)

    def mistake_density(self, state: TopicKnowledgeState) -> float:
        """Mistakes relative to attempts, not raw count, so a topic
        studied 40 times with 4 mistakes doesn't outrank one studied
        3 times with 2 mistakes."""
        attempts = len(state.quiz_history)
        if attempts == 0:
            return 0.0
        return clamp(state.mistake_count / attempts, 0.0, 1.0)

    def topic_priority(
        self, state: TopicKnowledgeState, as_of: date
    ) -> TopicRecommendation:
        f_risk = compute_forgetting_risk(state, as_of)
        urgency = self.exam_urgency(state, as_of)
        diff = self.difficulty_score(state)
        mistakes = self.mistake_density(state)

        w = self.weights
        score = (
            w["forgetting_risk"] * f_risk
            + w["exam_urgency"] * urgency
            + w["difficulty"] * diff
            + w["mistake_density"] * mistakes
        )
        score = round(clamp(score, 0.0, 1.0), 4)

        explanation = self._explain(state, as_of, f_risk, urgency, diff, mistakes)

        return TopicRecommendation(
            topic_id=state.topic_id,
            topic_name=state.topic_name,
            subject=state.subject,
            forgetting_risk=f_risk,
            exam_urgency=urgency,
            difficulty_score=diff,
            mistake_density=mistakes,
            priority_score=score,
            explanation=explanation,
        )

    def _explain(
        self,
        state: TopicKnowledgeState,
        as_of: date,
        f_risk: float,
        urgency: float,
        diff: float,
        mistakes: float,
    ) -> str:
        reasons = []
        days_left = state.days_until_exam(as_of)
        days_since = state.days_since_review(as_of)

        if f_risk > 0.5:
            reasons.append(
                f"you haven't reviewed it in {days_since} days and it's slipping fast"
            )
        elif f_risk > 0.25:
            reasons.append(f"retention is starting to fade ({days_since} days since last review)")

        if urgency > 0.5:
            reasons.append(f"the exam is only {days_left} days away")

        if mistakes > 0.4:
            reasons.append("you've been getting it wrong more often than not in quizzes")

        if diff > 0.75:
            reasons.append("it's a high-difficulty topic that needs more passes")

        if not reasons:
            return "Low priority right now — retention and timing both look fine."

        return "Recommended because " + "; and ".join(reasons) + "."

    def rank_topics(
        self, states: List[TopicKnowledgeState], as_of: date
    ) -> List[TopicRecommendation]:
        recs = [self.topic_priority(s, as_of) for s in states]
        recs.sort(key=lambda r: r.priority_score, reverse=True)
        return recs

    # ---------- AI disagreement feature ----------

    def register_disagreement(
        self,
        state: TopicKnowledgeState,
        student_claimed_confidence: float,
        reason: str,
        as_of: date,
        override_days: int = 3,
    ) -> DisagreementEvent:
        """Student pushes back on a recommendation (e.g. 'I already know
        this, stop nagging me about it'). We temporarily trust the
        student's self-assessment rather than silently overriding the
        model, and we log it so both sides of the disagreement are
        auditable. The override expires on its own -- if the student was
        right, the next quiz attempt will confirm it and the Twin's
        confidence will catch up; if they were wrong, the override lapses
        and the model's own signal takes back over."""
        expires = as_of + timedelta(days=override_days)
        state.student_override_confidence = clamp(student_claimed_confidence, 0.0, 1.0)
        state.override_expires = expires

        event = DisagreementEvent(
            topic_id=state.topic_id,
            student_claimed_confidence=student_claimed_confidence,
            reason=reason,
            date_raised=as_of,
            expires=expires,
        )
        self.disagreement_log.append(event)
        return event

    def reconcile_disagreement(
        self, state: TopicKnowledgeState, next_quiz_correct: bool
    ) -> str:
        """Call this once the student's next quiz result comes in for a
        topic under an active override. Returns a message describing how
        the disagreement was resolved."""
        if state.student_override_confidence is None:
            return "No active disagreement to reconcile for this topic."

        if next_quiz_correct:
            # Student was right -- let the override lapse naturally by
            # folding it into the real confidence and clearing the flag.
            state.confidence = max(state.confidence, state.student_override_confidence)
            state.student_override_confidence = None
            state.override_expires = None
            return "Student's self-assessment was confirmed by quiz results. AI recommendation updated to agree."
        else:
            # Student was wrong -- drop the override immediately and let
            # the model's forgetting-risk signal take back over.
            state.student_override_confidence = None
            state.override_expires = None
            state.mistake_count += 1
            return "Quiz result contradicted the student's self-assessment. Reverting to the AI's recommendation."

    # ---------- Sanity-check evaluator ----------

    def evaluate_predictions(
        self, recs: List[TopicRecommendation], states: List[TopicKnowledgeState], as_of: date
    ) -> List[str]:
        """Runs basic sanity checks over the engine's own output so obvious
        modeling bugs surface immediately instead of silently reaching the
        student. Returns a list of human-readable warnings (empty = clean)."""
        warnings = []
        by_id = {s.topic_id: s for s in states}

        for rec in recs:
            state = by_id[rec.topic_id]

            if not (0.0 <= rec.priority_score <= 1.0):
                warnings.append(f"{rec.topic_name}: priority score out of bounds ({rec.priority_score})")

            if not (0.0 <= rec.forgetting_risk <= 1.0):
                warnings.append(f"{rec.topic_name}: forgetting risk out of bounds ({rec.forgetting_risk})")

            if state.days_until_exam(as_of) < 0 and rec.priority_score < 0.9:
                warnings.append(
                    f"{rec.topic_name}: exam date has already passed but priority isn't maxed out"
                )

            if state.effective_confidence(as_of) > 0.9 and rec.forgetting_risk > 0.7:
                warnings.append(
                    f"{rec.topic_name}: high confidence but high forgetting risk — check stability inputs"
                )

        # Cross-topic check: ranking should be monotonically non-increasing.
        for i in range(len(recs) - 1):
            if recs[i].priority_score < recs[i + 1].priority_score:
                warnings.append("Ranking is not sorted correctly — sort invariant broken.")
                break

        return warnings
