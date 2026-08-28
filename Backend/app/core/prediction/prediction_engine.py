"""
prediction_engine.py

Person 4's Prediction + Adaptive Intelligence layer.

Sits ON TOP OF Person 1's KnowledgeTwinEngine — it never recomputes
confidence or decay math itself (that's forgetting_model.py's job, owned
by Person 1). Instead it takes the twin's outputs (confidence, forgetting
risk, exam_weight, exam_date, history) and turns them into a ranked,
explainable priority list, plus two extra things the pitch calls out
specifically:

  1. A sanity-check pass over the engine's own output, so obviously broken
     predictions get caught before they reach a judge or the dashboard.
  2. The "AI disagreement" feature — the student can push back on the
     twin's belief about a topic, and instead of either blindly obeying
     or blindly ignoring them, the engine applies a temporary, explainable
     discount and waits for a quiz result to settle who was right.

Owns:
    - exam urgency calculation (from exam_date)
    - topic priority score (forgetting risk + exam urgency + exam weight + mistake density)
    - a ranked list of topics with human-readable explanations
    - evaluate_predictions(): the sanity-check pass
    - register_disagreement() / reconcile_disagreement(): the disagreement feature
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Optional

from ..knowledge_twin.knowledge_twin_engine import KnowledgeTwinEngine


# ----------------------------------------------------------------------
# Tunable weights — how much each factor contributes to priority_score.
# Kept as named constants (not magic numbers) so they're easy to explain
# on stage and easy to retune during testing. They sum to 1.0.
# ----------------------------------------------------------------------
WEIGHT_FORGETTING_RISK = 0.40
WEIGHT_EXAM_URGENCY = 0.35
WEIGHT_EXAM_IMPORTANCE = 0.15
WEIGHT_MISTAKE_DENSITY = 0.10

URGENCY_HORIZON_DAYS = 14.0    # exams further out than this contribute ~0 urgency
EXAM_WEIGHT_CEILING = 1.5      # exam_weight value treated as "maximally important"
DISAGREEMENT_DEFAULT_OVERRIDE_DAYS = 3
DISAGREEMENT_DISCOUNT = 0.5    # soft discount, not a full override


@dataclass
class RankedTopic:
    """One topic's full priority breakdown — the contract the planner
    and the frontend ("why is ExamPilot recommending this?") consume."""
    topic: str
    priority_score: float
    forgetting_risk: float
    exam_urgency: float
    exam_weight: float
    mistake_density: float
    confidence_now: float
    days_until_exam: Optional[float]
    explanation: str
    overridden: bool = False


@dataclass
class DisagreementEvent:
    """Logged when a student pushes back on the twin's belief about a topic."""
    topic: str
    student_claimed_confidence: float   # 0-100
    twin_confidence_at_time: float
    reason: str
    logged_at: datetime
    expires: datetime
    resolved: bool = False
    resolution: str = ""


class PredictionEngine:
    def __init__(self, twin: KnowledgeTwinEngine):
        self.twin = twin
        self._disagreements: dict = {}   # topic -> DisagreementEvent (one active per topic)

    # ------------------------------------------------------------------
    # Exam urgency
    # ------------------------------------------------------------------
    def _days_until_exam(self, topic: str, at_time: Optional[datetime] = None) -> Optional[float]:
        exam_date = self.twin.topics[topic].exam_date
        if exam_date is None:
            return None
        at_time = at_time or datetime.now()
        return float((exam_date - at_time.date()).days)

    def exam_urgency(self, topic: str, at_time: Optional[datetime] = None) -> float:
        """
        0-1 score. 1.0 = exam is today/overdue. 0.0 = exam is far away, OR
        no exam date is known yet (no unfair penalty for topics that just
        haven't been scheduled — treated as "not urgent", not "urgent").

        Deliberately a simple linear ramp inside URGENCY_HORIZON_DAYS rather
        than something exponential — easy to explain on stage: "urgency
        rises steadily as the exam approaches, and maxes out a day or two out."
        """
        days_left = self._days_until_exam(topic, at_time)
        if days_left is None:
            return 0.0
        if days_left <= 1:
            return 1.0
        if days_left >= URGENCY_HORIZON_DAYS:
            return 0.0
        return round(1.0 - (days_left / URGENCY_HORIZON_DAYS), 3)

    # ------------------------------------------------------------------
    # Mistake density — proxy for "how hard THIS topic is for THIS student"
    # ------------------------------------------------------------------
    def mistake_density(self, topic: str) -> float:
        """
        Fraction of this topic's logged actions that were mistakes.
        Derived from Person 1's history log rather than a separate
        "difficulty" field — a topic can be objectively easy but still
        mistake-heavy for one particular student, which is the more
        useful, personalized signal here.
        """
        history = self.twin.topics[topic].history
        if not history:
            return 0.0
        mistakes = sum(1 for e in history if e.action_type == "mistake")
        return round(mistakes / len(history), 3)

    # ------------------------------------------------------------------
    # AI-disagreement discount (internal helper)
    # ------------------------------------------------------------------
    def _discount_for(self, topic: str, at_time: Optional[datetime] = None):
        event = self._disagreements.get(topic)
        if event is None:
            return 1.0, False
        at_time = at_time or datetime.now()
        if at_time > event.expires:
            return 1.0, False
        return DISAGREEMENT_DISCOUNT, True

    # ------------------------------------------------------------------
    # Priority scoring
    # ------------------------------------------------------------------
    def priority_score(self, topic: str, hours_ahead: float = 24, at_time: Optional[datetime] = None) -> RankedTopic:
        state = self.twin.topics[topic]
        confidence_now = self.twin.get_current_confidence(topic, at_time)
        forgetting_risk = self.twin.get_forgetting_risk(topic, hours_ahead)
        urgency = self.exam_urgency(topic, at_time)
        mistake_dens = self.mistake_density(topic)
        days_left = self._days_until_exam(topic, at_time)

        risk_norm = max(0.0, min(1.0, forgetting_risk / 100.0))
        weight_norm = max(0.0, min(1.0, state.exam_weight / EXAM_WEIGHT_CEILING))

        raw_score = (
            WEIGHT_FORGETTING_RISK * risk_norm
            + WEIGHT_EXAM_URGENCY * urgency
            + WEIGHT_EXAM_IMPORTANCE * weight_norm
            + WEIGHT_MISTAKE_DENSITY * mistake_dens
        )

        discount, overridden = self._discount_for(topic, at_time)
        final_score = round(raw_score * discount, 4)

        explanation = self._explain(topic, confidence_now, forgetting_risk, urgency, mistake_dens, days_left, overridden)

        return RankedTopic(
            topic=topic,
            priority_score=final_score,
            forgetting_risk=forgetting_risk,
            exam_urgency=urgency,
            exam_weight=state.exam_weight,
            mistake_density=mistake_dens,
            confidence_now=round(confidence_now, 1),
            days_until_exam=days_left,
            explanation=explanation,
            overridden=overridden,
        )

    def rank_topics(self, hours_ahead: float = 24, at_time: Optional[datetime] = None) -> list:
        scored = [self.priority_score(t, hours_ahead, at_time) for t in self.twin.topics]
        return sorted(scored, key=lambda r: r.priority_score, reverse=True)

    @staticmethod
    def _explain(topic, confidence_now, forgetting_risk, urgency, mistake_dens, days_left, overridden) -> str:
        parts = [f"{confidence_now:.0f}% confidence now, predicted to drop "
                 f"{forgetting_risk:.1f}% if left untouched."]
        if days_left is not None:
            parts.append(f"Exam in {days_left:.0f} day(s) (urgency {urgency:.0%}).")
        else:
            parts.append("No exam date set yet, so urgency isn't a factor.")
        if mistake_dens > 0.3:
            parts.append(f"Mistake-prone for you specifically ({mistake_dens:.0%} of logged actions).")
        if overridden:
            parts.append("Priority temporarily discounted — you flagged you feel confident here; being re-checked with a quiz.")
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Sanity-check evaluator — catches obviously broken output before
    # it reaches the judges or the dashboard.
    # ------------------------------------------------------------------
    def evaluate_predictions(self, ranked: Optional[list] = None, hours_ahead: float = 24) -> list:
        ranked = ranked if ranked is not None else self.rank_topics(hours_ahead)
        warnings = []

        scores = [r.priority_score for r in ranked]
        if scores and (max(scores) - min(scores)) < 0.02:
            warnings.append(
                "All topics have near-identical priority scores — recommendation may not be discriminating enough."
            )

        for r in ranked:
            if r.confidence_now >= 95 and r.priority_score > 0.5:
                warnings.append(
                    f"{r.topic}: confidence is very high ({r.confidence_now:.0f}%) but priority is still high "
                    f"— check exam_weight/exam_date inputs."
                )
            if r.days_until_exam is not None and r.days_until_exam < 0:
                warnings.append(
                    f"{r.topic}: exam_date is in the past ({r.days_until_exam:.0f} days ago) — stale data, refresh or exclude it."
                )
            if r.forgetting_risk < 0:
                warnings.append(
                    f"{r.topic}: forgetting_risk is negative ({r.forgetting_risk}) — confidence increased instead of "
                    f"decaying, check the inputs going into Person 1's engine."
                )

        return warnings

    # ------------------------------------------------------------------
    # AI disagreement feature
    # ------------------------------------------------------------------
    def register_disagreement(
        self,
        topic: str,
        student_claimed_confidence: float,
        reason: str,
        at_time: Optional[datetime] = None,
        override_days: float = DISAGREEMENT_DEFAULT_OVERRIDE_DAYS,
    ) -> DisagreementEvent:
        """
        Student pushes back: "I already know this, stop recommending it."
        We don't just obey — we log the claim, apply a soft priority
        discount for `override_days`, and wait for real evidence (a quiz)
        to settle it. This is the "AI coaches, doesn't obey" behavior.
        """
        if topic not in self.twin.topics:
            raise ValueError(f"Unknown topic: {topic}")
        at_time = at_time or datetime.now()
        event = DisagreementEvent(
            topic=topic,
            student_claimed_confidence=student_claimed_confidence,
            twin_confidence_at_time=self.twin.get_current_confidence(topic, at_time),
            reason=reason,
            logged_at=at_time,
            expires=at_time + timedelta(days=override_days),
        )
        self._disagreements[topic] = event
        return event

    def reconcile_disagreement(self, topic: str, next_quiz_correct: bool) -> str:
        """
        Call once the student's next quiz result on this topic comes in.
        Correct answer -> student was right, discount stays in place for
        the remaining window (no punitive re-ranking). Wrong answer ->
        twin was right, discount is lifted immediately and priority is
        restored to full.
        """
        event = self._disagreements.get(topic)
        if event is None:
            return f"No active disagreement logged for {topic}."

        event.resolved = True
        if next_quiz_correct:
            event.resolution = "Student was right — confidence claim upheld."
            return f"{topic}: quiz confirmed the student's claim. Disagreement resolved in the student's favor."
        else:
            event.resolution = "Student was overconfident — twin's original assessment upheld."
            del self._disagreements[topic]
            return f"{topic}: quiz proved the twin right. Priority restored — recommend revisiting {topic} now."
