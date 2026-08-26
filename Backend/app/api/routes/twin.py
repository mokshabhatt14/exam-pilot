"""
app/api/routes/twin.py

REST API surface for the Knowledge Twin Engine. This is what the frontend
(dashboard) and the study-planner service call — they never touch
knowledge_twin_engine.py directly.

NOTE: this uses one in-memory engine per student, keyed by student_id, just
to get the team moving without a database. Swap _get_engine() for a real
DB-backed load/save once persistence is needed — the rest of this file
doesn't need to change.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.knowledge_twin.knowledge_twin_engine import KnowledgeTwinEngine

router = APIRouter(prefix="/twin", tags=["Knowledge Twin"])

# --- Temporary in-memory store: student_id -> KnowledgeTwinEngine ---
# Replace with real persistence (DB) later; keep the function signature the same.
_ENGINES: dict = {}

DEFAULT_TOPICS = ["Arrays", "Trees", "Graphs", "DP", "OS"]
DEFAULT_WEIGHTS = {"Arrays": 0.8, "Trees": 1.0, "Graphs": 1.2, "DP": 1.3, "OS": 0.9}


def _get_engine(student_id: str) -> KnowledgeTwinEngine:
    if student_id not in _ENGINES:
        _ENGINES[student_id] = KnowledgeTwinEngine(DEFAULT_TOPICS, DEFAULT_WEIGHTS)
    return _ENGINES[student_id]


# --- Request/response schemas ---
class ActionRequest(BaseModel):
    student_id: str
    topic: str
    action_type: str  # "studied" | "quiz" | "revision" | "mistake" | "skipped"
    quiz_score: Optional[float] = None
    note: Optional[str] = ""


class RecommendationResponse(BaseModel):
    recommended_topic: str
    explanation: str


# --- Endpoints ---
@router.post("/action")
def record_action(payload: ActionRequest):
    """Call this every time a student does something (studies, takes a quiz, etc.)."""
    engine = _get_engine(payload.student_id)
    try:
        event = engine.record_action(
            topic=payload.topic,
            action_type=payload.action_type,
            quiz_score=payload.quiz_score,
            note=payload.note or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "topic": payload.topic,
        "confidence_after": round(event.confidence_after, 1),
        "stability_after": round(event.stability_after, 2),
    }


@router.get("/state/{student_id}")
def get_current_state(student_id: str):
    """The 'You / Your AI Twin' current confidence map for the dashboard."""
    engine = _get_engine(student_id)
    return engine.get_confidence_map()


@router.get("/predict/{student_id}")
def get_predicted_state(student_id: str, hours_ahead: float = 24):
    """The 'Tomorrow' panel — predicted confidence if the student does nothing."""
    engine = _get_engine(student_id)
    return engine.predict_confidence_map(hours_ahead=hours_ahead)


@router.get("/risk/{student_id}")
def get_forgetting_risk(student_id: str, hours_ahead: float = 24):
    """Predicted confidence drop per topic — feeds the 'arrows' in the pitch UI."""
    engine = _get_engine(student_id)
    return engine.get_forgetting_risk_map(hours_ahead=hours_ahead)


@router.get("/recommend/{student_id}", response_model=RecommendationResponse)
def get_recommendation(student_id: str, hours_ahead: float = 24):
    """What should the student study next, and the explainable reason why."""
    engine = _get_engine(student_id)
    topic = engine.recommend_next_topic(hours_ahead=hours_ahead)
    explanation = engine.explain(topic, hours_ahead=hours_ahead)
    return RecommendationResponse(recommended_topic=topic, explanation=explanation)


@router.get("/snapshot/{student_id}")
def get_full_snapshot(student_id: str):
    """Full state dump — useful for debugging or an admin/judge view."""
    engine = _get_engine(student_id)
    return engine.snapshot()
