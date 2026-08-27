from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    Student,
    Subject,
    Topic,
    Quiz,
    QuizAttempt,
    StudySession,
    KnowledgeState,
)

router = APIRouter(prefix="/api", tags=["Data"])


# ---------- REQUEST SCHEMAS ----------

class StudentCreate(BaseModel):
    name: str
    email: str | None = None


class SubjectCreate(BaseModel):
    student_id: int
    name: str
    exam_date: str | None = None


class TopicCreate(BaseModel):
    subject_id: int
    name: str
    description: str | None = None
    difficulty: str | None = None


class QuizCreate(BaseModel):
    subject_id: int
    topic_id: int | None = None
    title: str


class QuizAttemptCreate(BaseModel):
    student_id: int
    score: float
    total_questions: int


class StudySessionCreate(BaseModel):
    student_id: int
    topic_id: int
    duration_minutes: int
    session_type: str | None = None


class KnowledgeStateUpdate(BaseModel):
    confidence: float
    retention: float = 0.0
    mastery: float = 0.0
    forgetting_risk: float = 0.0
    mistake_count: int = 0
    revision_count: int = 0
    quiz_accuracy: float = 0.0


# ---------- STUDENTS ----------

@router.post("/students")
def create_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db),
):
    student = Student(
        name=student_data.name,
        email=student_data.email,
    )

    try:
        db.add(student)
        db.commit()
        db.refresh(student)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A student with this email already exists.",
        )

    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
    }


@router.get("/students/{student_id}")
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
    }


# ---------- SUBJECTS ----------

@router.post("/subjects")
def create_subject(
    data: SubjectCreate,
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == data.student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    subject = Subject(
        student_id=data.student_id,
        name=data.name,
        exam_date=data.exam_date,
    )

    db.add(subject)
    db.commit()
    db.refresh(subject)

    return {
        "id": subject.id,
        "student_id": subject.student_id,
        "name": subject.name,
        "exam_date": subject.exam_date,
    }


@router.get("/students/{student_id}/subjects")
def get_subjects(
    student_id: int,
    db: Session = Depends(get_db),
):
    subjects = (
        db.query(Subject)
        .filter(Subject.student_id == student_id)
        .all()
    )

    return [
        {
            "id": s.id,
            "name": s.name,
            "exam_date": s.exam_date,
        }
        for s in subjects
    ]


# ---------- TOPICS ----------

@router.post("/topics")
def create_topic(
    data: TopicCreate,
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    topic = Topic(
        subject_id=data.subject_id,
        name=data.name,
        description=data.description,
        difficulty=data.difficulty,
    )

    db.add(topic)
    db.commit()
    db.refresh(topic)

    return {
        "id": topic.id,
        "subject_id": topic.subject_id,
        "name": topic.name,
        "description": topic.description,
        "difficulty": topic.difficulty,
    }


@router.get("/subjects/{subject_id}/topics")
def get_topics(
    subject_id: int,
    db: Session = Depends(get_db),
):
    topics = (
        db.query(Topic)
        .filter(Topic.subject_id == subject_id)
        .all()
    )

    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "difficulty": t.difficulty,
        }
        for t in topics
    ]


# ---------- QUIZZES ----------

@router.post("/quizzes")
def create_quiz(
    data: QuizCreate,
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if data.topic_id:
        topic = db.query(Topic).filter(Topic.id == data.topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

    quiz = Quiz(
        subject_id=data.subject_id,
        topic_id=data.topic_id,
        title=data.title,
    )

    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    return {
        "id": quiz.id,
        "title": quiz.title,
        "subject_id": quiz.subject_id,
        "topic_id": quiz.topic_id,
    }


@router.post("/quizzes/{quiz_id}/attempts")
def submit_quiz_attempt(
    quiz_id: int,
    data: QuizAttemptCreate,
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if data.total_questions <= 0:
        raise HTTPException(
            status_code=400,
            detail="total_questions must be greater than zero",
        )

    if data.score < 0 or data.score > data.total_questions:
        raise HTTPException(
            status_code=400,
            detail="score must be between 0 and total_questions",
        )

    accuracy = data.score / data.total_questions

    attempt = QuizAttempt(
        quiz_id=quiz_id,
        student_id=data.student_id,
        score=data.score,
        total_questions=data.total_questions,
        accuracy=accuracy,
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "score": attempt.score,
        "total_questions": attempt.total_questions,
        "accuracy": round(attempt.accuracy, 2),
    }


# ---------- STUDY SESSIONS ----------

@router.post("/study-sessions")
def create_study_session(
    data: StudySessionCreate,
    db: Session = Depends(get_db),
):
    if data.duration_minutes <= 0:
        raise HTTPException(
            status_code=400,
            detail="duration_minutes must be greater than zero",
        )

    student = db.query(Student).filter(Student.id == data.student_id).first()
    topic = db.query(Topic).filter(Topic.id == data.topic_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    session = StudySession(
        student_id=data.student_id,
        topic_id=data.topic_id,
        duration_minutes=data.duration_minutes,
        session_type=data.session_type,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "student_id": session.student_id,
        "topic_id": session.topic_id,
        "duration_minutes": session.duration_minutes,
        "session_type": session.session_type,
    }


# ---------- KNOWLEDGE STATE ----------

@router.get("/students/{student_id}/knowledge-state")
def get_knowledge_states(
    student_id: int,
    db: Session = Depends(get_db),
):
    states = (
        db.query(KnowledgeState)
        .filter(KnowledgeState.student_id == student_id)
        .all()
    )

    return [
        {
            "topic_id": state.topic_id,
            "confidence": state.confidence,
            "retention": state.retention,
            "mastery": state.mastery,
            "forgetting_risk": state.forgetting_risk,
            "mistake_count": state.mistake_count,
            "revision_count": state.revision_count,
            "quiz_accuracy": state.quiz_accuracy,
        }
        for state in states
    ]


@router.put("/students/{student_id}/topics/{topic_id}/knowledge-state")
def update_knowledge_state(
    student_id: int,
    topic_id: int,
    data: KnowledgeStateUpdate,
    db: Session = Depends(get_db),
):
    if not 0 <= data.confidence <= 1:
        raise HTTPException(status_code=400, detail="confidence must be between 0 and 1")

    if not 0 <= data.retention <= 1:
        raise HTTPException(status_code=400, detail="retention must be between 0 and 1")

    if not 0 <= data.mastery <= 1:
        raise HTTPException(status_code=400, detail="mastery must be between 0 and 1")

    if not 0 <= data.forgetting_risk <= 1:
        raise HTTPException(status_code=400, detail="forgetting_risk must be between 0 and 1")

    state = (
        db.query(KnowledgeState)
        .filter(
            KnowledgeState.student_id == student_id,
            KnowledgeState.topic_id == topic_id,
        )
        .first()
    )

    if not state:
        state = KnowledgeState(
            student_id=student_id,
            topic_id=topic_id,
        )
        db.add(state)

    state.confidence = data.confidence
    state.retention = data.retention
    state.mastery = data.mastery
    state.forgetting_risk = data.forgetting_risk
    state.mistake_count = data.mistake_count
    state.revision_count = data.revision_count
    state.quiz_accuracy = data.quiz_accuracy
    state.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(state)

    return {
        "student_id": student_id,
        "topic_id": topic_id,
        "confidence": state.confidence,
        "retention": state.retention,
        "mastery": state.mastery,
        "forgetting_risk": state.forgetting_risk,
    }