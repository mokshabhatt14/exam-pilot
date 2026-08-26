"""
forgetting_model.py

Implements the "forgetting curve" — the actual predictive math behind
the Knowledge Twin. Based on the Ebbinghaus forgetting curve, adapted
with a SuperMemo-style "stability" parameter so that well-revised
topics decay slower than freshly-seen ones.

Core formula:
    confidence(t) = confidence_0 * exp(-t / stability)

Where:
    confidence_0 = confidence right after the last update
    t            = elapsed time since last_updated, in days
    stability    = how many days it takes to lose ~63% of confidence
                   if nothing is done (bigger = "sticks better")

This is intentionally simple and explainable — a judge or teammate can
read this file in 30 seconds and understand exactly why the twin
predicts what it predicts. That's worth more at a hackathon than a
fancier model nobody can explain on stage.
"""

import math
from datetime import datetime

# Tunable constants — adjust these to change how "forgetful" the twin is.
# Calibrated so a single decent study session (stability ~3-4 days) still
# leaves meaningful confidence after ~5-6 days of no contact, matching a
# realistic Ebbinghaus-style curve rather than crashing to ~0.
MIN_STABILITY_DAYS = 1.5     # floor, so we never divide by ~0 or decay instantly
MAX_STABILITY_DAYS = 30.0    # ceiling, so a topic never becomes "unforgettable"


def decay_confidence(confidence_0: float, stability_days: float, elapsed_days: float) -> float:
    """Predict confidence after `elapsed_days` of no interaction."""
    stability_days = max(stability_days, MIN_STABILITY_DAYS)
    decayed = confidence_0 * math.exp(-elapsed_days / stability_days)
    return max(0.0, min(100.0, decayed))


def elapsed_days_since(last_updated: datetime, at_time: datetime = None) -> float:
    at_time = at_time or datetime.now()
    delta = at_time - last_updated
    return max(0.0, delta.total_seconds() / 86400.0)


def update_stability(current_stability: float, action_type: str, quality: float = 1.0) -> float:
    """
    Adjust stability after an action. `quality` is 0-1 and represents how
    "good" the action was — e.g. a high quiz score or a confident revision
    increases stability more than a shaky one.

    Rules of thumb (tune during testing):
    - studied:   modest bump, student has seen it again
    - revision:  bigger bump, deliberate spaced-repetition-style review
    - quiz:      bump scaled directly by score quality
    - mistake:   stability drops — the topic is proving less "sticky" than assumed
    - skipped:   no change to stability itself (decay handles the cost of skipping)
    """
    if action_type == "studied":
        new_stability = current_stability + 1.5 * quality
    elif action_type == "revision":
        new_stability = current_stability + 3.0 * quality
    elif action_type == "quiz":
        # quiz quality below 0.5 actively hurts stability; above it, helps
        new_stability = current_stability + (quality - 0.5) * 4.0
    elif action_type == "mistake":
        new_stability = current_stability - 1.5
    else:  # "skipped" or unknown action types
        new_stability = current_stability

    return max(MIN_STABILITY_DAYS, min(MAX_STABILITY_DAYS, new_stability))


def update_confidence(current_confidence: float, action_type: str, quiz_score: float = None) -> float:
    """
    Compute the new "confidence_0" right after an action (before any decay
    is applied). This is the immediate effect of the action, separate from
    the forgetting curve that kicks in afterward.
    """
    if action_type == "studied":
        new_confidence = current_confidence + 8
    elif action_type == "revision":
        new_confidence = current_confidence + 12
    elif action_type == "quiz":
        score = quiz_score if quiz_score is not None else current_confidence
        # Quiz result pulls confidence toward the actual demonstrated score,
        # rather than fully overwriting it — one bad quiz shouldn't erase
        # a long revision history instantly.
        new_confidence = (current_confidence * 0.4) + (score * 0.6)
    elif action_type == "mistake":
        new_confidence = current_confidence - 10
    else:  # "skipped"
        new_confidence = current_confidence

    return max(0.0, min(100.0, new_confidence))
