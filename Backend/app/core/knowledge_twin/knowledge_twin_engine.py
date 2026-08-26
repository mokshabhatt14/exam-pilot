"""
knowledge_twin_engine.py

The Knowledge Twin Engine — the "brain" of ExamPilot's Person 1 module.

Owns one TopicState per syllabus topic for a student, and exposes:
  - record_action(): the single entry point every student action flows through
  - get_confidence_map(): "what does the twin believe right now"
  - predict_confidence_map(): "what will the twin believe at some future time"
  - recommend_next_topic(): "what should the student study next, and why"
  - explain(): natural-language justification for the recommendation
                (this is your explainable-AI story for the judges)

This file is deliberately the ONLY place that other modules (dashboard,
planner, backend API) need to import from. Everything else (knowledge_state,
forgetting_model) is an internal implementation detail.
"""

from datetime import datetime, timedelta
from typing import Optional

from .knowledge_state import TopicState, ActionEvent
from . import forgetting_model as fm


class KnowledgeTwinEngine:
    def __init__(self, topics: list, exam_weights: Optional[dict] = None):
        """
        topics: list of topic names, e.g. ["Arrays", "Trees", "Graphs", "DP", "OS"]
        exam_weights: optional dict topic -> relative importance (default 1.0 each)
        """
        exam_weights = exam_weights or {}
        self.topics: dict = {
            t: TopicState(topic=t, exam_weight=exam_weights.get(t, 1.0))
            for t in topics
        }

    # ------------------------------------------------------------------
    # Writing: every student action flows through here
    # ------------------------------------------------------------------
    def record_action(
        self,
        topic: str,
        action_type: str,
        quiz_score: Optional[float] = None,
        note: str = "",
        at_time: Optional[datetime] = None,
    ) -> ActionEvent:
        """
        action_type: "studied" | "quiz" | "revision" | "mistake" | "skipped"
        quiz_score: 0-100, required (recommended) when action_type == "quiz"
        """
        if topic not in self.topics:
            raise ValueError(f"Unknown topic: {topic}")

        state = self.topics[topic]
        at_time = at_time or datetime.now()

        # 1. Apply decay up to "now" before this new action modifies anything,
        #    so the "before" snapshot in the log reflects reality, not a stale value.
        elapsed = fm.elapsed_days_since(state.last_updated, at_time)
        confidence_before = fm.decay_confidence(state.confidence, state.stability, elapsed)
        stability_before = state.stability

        # 2. Compute quality signal for stability updates (mainly used by quizzes)
        quality = (quiz_score / 100.0) if quiz_score is not None else 0.75

        # 3. Apply the action's immediate effect
        confidence_after = fm.update_confidence(confidence_before, action_type, quiz_score)
        stability_after = fm.update_stability(stability_before, action_type, quality)

        # 4. Commit new state
        state.confidence = confidence_after
        state.stability = stability_after
        state.last_updated = at_time

        event = ActionEvent(
            action_type=action_type,
            timestamp=at_time,
            detail=note or self._auto_note(action_type, quiz_score),
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            stability_before=stability_before,
            stability_after=stability_after,
        )
        state.log(event)
        return event

    @staticmethod
    def _auto_note(action_type: str, quiz_score: Optional[float]) -> str:
        if action_type == "quiz" and quiz_score is not None:
            return f"quiz score {quiz_score:.0f}%"
        return action_type

    # ------------------------------------------------------------------
    # Reading: current state (with decay applied on read)
    # ------------------------------------------------------------------
    def get_current_confidence(self, topic: str, at_time: Optional[datetime] = None) -> float:
        state = self.topics[topic]
        at_time = at_time or datetime.now()
        elapsed = fm.elapsed_days_since(state.last_updated, at_time)
        return fm.decay_confidence(state.confidence, state.stability, elapsed)

    def get_confidence_map(self, at_time: Optional[datetime] = None) -> dict:
        return {t: round(self.get_current_confidence(t, at_time), 1) for t in self.topics}

    # ------------------------------------------------------------------
    # Predicting: the actual "twin" behavior — projecting forward in time
    # ------------------------------------------------------------------
    def predict_confidence(self, topic: str, hours_ahead: float = 24) -> float:
        state = self.topics[topic]
        future_time = datetime.now() + timedelta(hours=hours_ahead)
        elapsed = fm.elapsed_days_since(state.last_updated, future_time)
        return fm.decay_confidence(state.confidence, state.stability, elapsed)

    def predict_confidence_map(self, hours_ahead: float = 24) -> dict:
        return {t: round(self.predict_confidence(t, hours_ahead), 1) for t in self.topics}

    def get_forgetting_risk(self, topic: str, hours_ahead: float = 24) -> float:
        """Predicted drop in confidence over the window. Higher = more urgent."""
        now_conf = self.get_current_confidence(topic)
        future_conf = self.predict_confidence(topic, hours_ahead)
        return round(now_conf - future_conf, 1)

    def get_forgetting_risk_map(self, hours_ahead: float = 24) -> dict:
        return {t: self.get_forgetting_risk(t, hours_ahead) for t in self.topics}

    # ------------------------------------------------------------------
    # Deciding: turn predictions into a recommendation
    # ------------------------------------------------------------------
    def recommend_next_topic(self, hours_ahead: float = 24) -> str:
        """
        Pick the topic that maximizes (forgetting risk * exam weight) —
        i.e. the topic that's both important AND about to be forgotten.
        This is the "AI coaching, not obeying" behavior from the pitch.
        """
        scored = {
            t: self.get_forgetting_risk(t, hours_ahead) * self.topics[t].exam_weight
            for t in self.topics
        }
        return max(scored, key=scored.get)

    # ------------------------------------------------------------------
    # Explaining: the judge-facing "why" behind a recommendation
    # ------------------------------------------------------------------
    def explain(self, topic: str, hours_ahead: float = 24) -> str:
        state = self.topics[topic]
        now_conf = self.get_current_confidence(topic)
        future_conf = self.predict_confidence(topic, hours_ahead)
        drop = round(now_conf - future_conf, 1)
        days_since_touch = round(fm.elapsed_days_since(state.last_updated), 1)

        window_label = "tomorrow" if 20 <= hours_ahead <= 30 else f"in {hours_ahead:.0f}h"

        return (
            f"Your twin predicts you'll lose about {drop}% confidence in "
            f"{topic} by {window_label}, because it's been {days_since_touch} day(s) "
            f"since you last touched it and your current confidence is only "
            f"{now_conf:.0f}%. Recommend revising {topic} next."
        )

    # ------------------------------------------------------------------
    # Serialization — the contract for other modules to consume
    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        return {t: s.to_dict() for t, s in self.topics.items()}
