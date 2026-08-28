"""
study_planner.py

Turns PredictionEngine's ranked topics into two things a student can
actually act on:

  1. An adaptive study plan — how to split available minutes across topics.
  2. Simulation mode — "what happens if I don't study X for N more days",
     and "what does studying today actually buy me by exam day".

Nothing here recomputes confidence/decay math itself — every number goes
through Person 1's forgetting_model via the twin, so results here are
always consistent with what the dashboard shows.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Optional

from .prediction_engine import PredictionEngine
from ..knowledge_twin import forgetting_model as fm

MIN_MINUTES_PER_TOPIC = 5   # don't bother allocating a token 1-2 minute slot


@dataclass
class StudyPlanItem:
    topic: str
    allocated_minutes: int
    priority_score: float
    reason: str


@dataclass
class SimulationPoint:
    day_offset: int
    calendar_date: date
    retention: float   # 0-1, i.e. confidence/100 at that future point


class AdaptiveStudyPlanner:
    def __init__(self, engine: PredictionEngine):
        self.engine = engine
        self.twin = engine.twin

    # ------------------------------------------------------------------
    # "What should I study right now?"
    # ------------------------------------------------------------------
    def what_to_study_next(self, session_size: int = 2, hours_ahead: float = 24) -> list:
        ranked = self.engine.rank_topics(hours_ahead=hours_ahead)
        return ranked[:session_size]

    # ------------------------------------------------------------------
    # Adaptive study plan — split total_minutes proportional to priority
    # ------------------------------------------------------------------
    def build_study_plan(self, total_minutes: int, hours_ahead: float = 24) -> list:
        ranked = [r for r in self.engine.rank_topics(hours_ahead=hours_ahead) if r.priority_score > 0]
        if not ranked:
            return []

        total_score = sum(r.priority_score for r in ranked)
        plan = []
        allocated_so_far = 0

        for i, r in enumerate(ranked):
            if i == len(ranked) - 1:
                # last item takes whatever's left so rounding never leaves minutes unassigned
                minutes = total_minutes - allocated_so_far
            else:
                share = r.priority_score / total_score
                minutes = int(round(total_minutes * share))
            if minutes < MIN_MINUTES_PER_TOPIC:
                continue
            plan.append(StudyPlanItem(
                topic=r.topic,
                allocated_minutes=minutes,
                priority_score=r.priority_score,
                reason=r.explanation,
            ))
            allocated_so_far += minutes

        return plan

    # ------------------------------------------------------------------
    # Simulation mode: project forward assuming NO further action
    # ------------------------------------------------------------------
    def simulate_forgetting(self, topic: str, days_ahead: int = 5, start: Optional[datetime] = None) -> list:
        state = self.twin.topics[topic]
        start = start or datetime.now()
        points = []
        for offset in range(days_ahead + 1):
            future_time = start + timedelta(days=offset)
            elapsed = fm.elapsed_days_since(state.last_updated, future_time)
            confidence = fm.decay_confidence(state.confidence, state.stability, elapsed)
            points.append(SimulationPoint(
                day_offset=offset,
                calendar_date=future_time.date(),
                retention=round(confidence / 100.0, 4),
            ))
        return points

    def simulate_exam_day_outcomes(self) -> dict:
        """For every topic with a known exam_date, project retention on
        that exam day assuming no further study happens between now and then."""
        outcomes = {}
        for topic, state in self.twin.topics.items():
            if state.exam_date is None:
                continue
            exam_dt = datetime.combine(state.exam_date, datetime.min.time())
            elapsed = fm.elapsed_days_since(state.last_updated, exam_dt)
            retention = fm.decay_confidence(state.confidence, state.stability, elapsed) / 100.0
            outcomes[topic] = (state.exam_date, round(retention, 4))
        return outcomes

    def simulate_plan_impact(self, topic: str, at_time: Optional[datetime] = None) -> tuple:
        """
        Returns (retention_without_studying_today, retention_if_reviewed_today),
        both projected forward to this topic's exam_date. Requires exam_date
        to be set on the topic.
        """
        state = self.twin.topics[topic]
        if state.exam_date is None:
            raise ValueError(f"{topic} has no exam_date set — can't project to exam day.")
        at_time = at_time or datetime.now()
        exam_dt = datetime.combine(state.exam_date, datetime.min.time())

        # Baseline: no further action, just decay from current state to exam day
        elapsed_baseline = fm.elapsed_days_since(state.last_updated, exam_dt)
        baseline = fm.decay_confidence(state.confidence, state.stability, elapsed_baseline) / 100.0

        # What-if: simulate a "revision" action today, then decay to exam day
        confidence_before = fm.decay_confidence(
            state.confidence, state.stability, fm.elapsed_days_since(state.last_updated, at_time)
        )
        confidence_after_review = fm.update_confidence(confidence_before, "revision")
        stability_after_review = fm.update_stability(state.stability, "revision", quality=1.0)
        elapsed_from_review = fm.elapsed_days_since(at_time, exam_dt) if exam_dt > at_time else 0.0
        projected = fm.decay_confidence(confidence_after_review, stability_after_review, elapsed_from_review) / 100.0

        return round(baseline, 4), round(projected, 4)
