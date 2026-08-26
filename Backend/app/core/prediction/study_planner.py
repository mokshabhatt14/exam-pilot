"""
study_planner.py

Builds on top of PredictionEngine to answer the actual product questions:
  - "What should I study right now?"
  - "Given I have 90 minutes today, how should I spend them?"
  - "What happens to my retention if I don't study X before the exam?"
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple

from knowledge_state import TopicKnowledgeState
from forgetting_model import compute_retention, compute_retention_on_date
from prediction_engine import PredictionEngine, TopicRecommendation


@dataclass
class PlanItem:
    topic_id: str
    topic_name: str
    subject: str
    allocated_minutes: int
    priority_score: float
    reason: str


@dataclass
class SimulationPoint:
    day_offset: int
    calendar_date: date
    retention: float


class AdaptiveStudyPlanner:
    def __init__(self, engine: PredictionEngine):
        self.engine = engine

    # ---------- "What should I study next?" ----------

    def what_to_study_next(
        self,
        states: List[TopicKnowledgeState],
        as_of: date,
        session_size: int = 3,
    ) -> List[TopicRecommendation]:
        ranked = self.engine.rank_topics(states, as_of)
        return ranked[:session_size]

    # ---------- Full time-budget plan ----------

    def build_study_plan(
        self,
        states: List[TopicKnowledgeState],
        as_of: date,
        total_minutes: int,
    ) -> List[PlanItem]:
        """Greedy allocation: rank by priority, then by priority-per-minute
        efficiency, and fill the available time budget. Every topic gets at
        most one review block per plan (a fuller version would let the
        student re-queue a topic across multiple sessions)."""
        ranked = self.engine.rank_topics(states, as_of)
        by_id = {s.topic_id: s for s in states}

        # Efficiency = priority achieved per minute spent. This keeps a
        # slightly-lower-priority-but-quick topic from being crowded out by
        # one long, only-marginally-more-urgent topic.
        scored = []
        for rec in ranked:
            state = by_id[rec.topic_id]
            minutes = max(state.review_time_minutes, 1)
            efficiency = rec.priority_score / minutes
            scored.append((efficiency, rec, state))

        scored.sort(key=lambda x: x[0], reverse=True)

        plan: List[PlanItem] = []
        remaining = total_minutes
        for _efficiency, rec, state in scored:
            if remaining <= 0:
                break
            minutes_needed = state.review_time_minutes
            if minutes_needed <= remaining:
                allocated = minutes_needed
            elif remaining >= 10:
                # Not enough time for a full review, but a partial pass on
                # the highest-priority remaining topic is still worth it.
                allocated = remaining
            else:
                continue

            plan.append(
                PlanItem(
                    topic_id=rec.topic_id,
                    topic_name=rec.topic_name,
                    subject=rec.subject,
                    allocated_minutes=allocated,
                    priority_score=rec.priority_score,
                    reason=rec.explanation,
                )
            )
            remaining -= allocated

        return plan

    # ---------- Simulation mode ----------

    def simulate_forgetting(
        self,
        state: TopicKnowledgeState,
        as_of: date,
        days_ahead: int,
        step_days: int = 1,
    ) -> List[SimulationPoint]:
        """Project this topic's retention curve forward assuming NO further
        review happens. This is the 'what happens if I ignore this' demo:
        judges can see the curve visibly fall off before the exam."""
        points = []
        day = 0
        while day <= days_ahead:
            target = as_of + timedelta(days=day)
            retention = compute_retention_on_date(state, as_of, target)
            points.append(SimulationPoint(day_offset=day, calendar_date=target, retention=round(retention, 4)))
            day += step_days
        return points

    def simulate_exam_day_outcomes(
        self, states: List[TopicKnowledgeState], as_of: date
    ) -> Dict[str, Tuple[date, float]]:
        """For every topic, project retention on ITS OWN exam date assuming
        no further review. Useful for a single 'if you stop studying now,
        here's how you'd do on exam day' summary screen."""
        outcomes = {}
        for state in states:
            projected = compute_retention_on_date(state, as_of, state.exam_date)
            outcomes[state.topic_id] = (state.exam_date, round(projected, 4))
        return outcomes

    def simulate_plan_impact(
        self,
        state: TopicKnowledgeState,
        as_of: date,
        boost_repetitions: int = 1,
    ) -> Tuple[float, float]:
        """Compare projected retention on the exam date with vs. without
        one additional review today. Used to show 'studying this today
        raises your exam-day retention from X% to Y%.'"""
        before = compute_retention_on_date(state, as_of, state.exam_date)

        # Simulate a review happening today: reset the clock and bump
        # repetitions, without mutating the real state object.
        import copy

        reviewed = copy.deepcopy(state)
        reviewed.last_reviewed = as_of
        reviewed.repetitions += boost_repetitions

        after = compute_retention_on_date(reviewed, as_of, state.exam_date)
        return round(before, 4), round(after, 4)
