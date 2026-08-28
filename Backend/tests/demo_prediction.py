"""
demo_prediction.py

End-to-end demonstration of Person 4's Prediction + Adaptive Intelligence
layer, built directly on top of Person 1's real KnowledgeTwinEngine — no
mock/fake schema. This is the actual contract the backend and frontend use.

Replaces the old demo.py, which imported a TopicKnowledgeState class
(ease_factor, quiz_history, difficulty, etc.) that never existed in
Person 1's real code, plus prediction_engine/study_planner modules that
hadn't been built yet.

Suggested location: Backend/tests/demo_prediction.py, alongside the
existing demo_knowledge_twin.py.

Usage:
    python -m tests.demo_prediction
(run from the Backend/ folder, so the app.* package imports resolve)
"""

from datetime import datetime, timedelta, date

from app.core.knowledge_twin.knowledge_twin_engine import KnowledgeTwinEngine
from app.core.prediction import PredictionEngine, AdaptiveStudyPlanner


def section(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    topics = ["Arrays", "Trees", "Graphs", "DP", "OS"]
    exam_weights = {"Arrays": 0.8, "Trees": 1.0, "Graphs": 1.2, "DP": 1.3, "OS": 0.9}

    today = date.today()
    exam_dates = {
        "Arrays": today + timedelta(days=10),
        "Trees": today + timedelta(days=10),
        "Graphs": today + timedelta(days=6),
        "DP": today + timedelta(days=6),
        "OS": today + timedelta(days=2),   # OS exam is soonest -> should push urgency up
    }

    twin = KnowledgeTwinEngine(topics, exam_weights, exam_dates)

    print("Simulating a week of study activity...")

    six_days_ago = datetime.now() - timedelta(days=6)
    twin.record_action("Arrays", "studied", at_time=six_days_ago)
    twin.record_action("Arrays", "quiz", quiz_score=95, at_time=six_days_ago)

    five_days_ago = datetime.now() - timedelta(days=5)
    twin.record_action("Trees", "revision", at_time=five_days_ago)
    twin.record_action("Trees", "quiz", quiz_score=70, at_time=five_days_ago)

    four_days_ago = datetime.now() - timedelta(days=4)
    twin.record_action("Graphs", "skipped", at_time=four_days_ago)
    twin.record_action("Graphs", "mistake", at_time=four_days_ago)

    twin.record_action("DP", "studied", at_time=six_days_ago)
    twin.record_action("DP", "quiz", quiz_score=58, at_time=six_days_ago)
    twin.record_action("DP", "mistake", at_time=four_days_ago)

    two_days_ago = datetime.now() - timedelta(days=2)
    twin.record_action("OS", "studied", at_time=two_days_ago)
    twin.record_action("OS", "mistake", at_time=two_days_ago)

    engine = PredictionEngine(twin)
    planner = AdaptiveStudyPlanner(engine)

    section("1. RANKED TOPICS (forgetting-risk + exam urgency + mistake density)")
    ranked = engine.rank_topics()
    for r in ranked:
        print(f"\n[{r.priority_score:.3f}] {r.topic}")
        print(f"   confidence_now={r.confidence_now}%  forgetting_risk={r.forgetting_risk}%  "
              f"exam_urgency={r.exam_urgency}  mistake_density={r.mistake_density}  "
              f"days_until_exam={r.days_until_exam}")
        print(f"   why: {r.explanation}")

    section("2. SANITY-CHECK EVALUATOR")
    warnings = engine.evaluate_predictions(ranked)
    print("\n".join(warnings) if warnings else "No issues found — output looks internally consistent.")

    section("3. WHAT SHOULD I STUDY RIGHT NOW? (top 2)")
    for r in planner.what_to_study_next(session_size=2):
        print(f"- {r.topic}: {r.explanation}")

    section("4. ADAPTIVE STUDY PLAN (60 minutes available today)")
    plan = planner.build_study_plan(total_minutes=60)
    for item in plan:
        print(f"- {item.allocated_minutes} min -> {item.topic} (priority {item.priority_score:.3f})")
    print(f"Total allocated: {sum(i.allocated_minutes for i in plan)}/60 minutes")

    section("5. SIMULATION MODE — Graphs, next 5 days, no review")
    for point in planner.simulate_forgetting("Graphs", days_ahead=5):
        bar = "#" * int(point.retention * 30)
        print(f"day {point.day_offset} ({point.calendar_date}): {point.retention:.2%} {bar}")

    section("6. EXAM-DAY OUTCOME IF NOTHING IS STUDIED FURTHER")
    for topic, (exam_date, retention) in planner.simulate_exam_day_outcomes().items():
        print(f"- {topic}: projected {retention:.2%} retention on exam day ({exam_date})")

    section("7. IMPACT OF STUDYING TODAY — OS (exam in 2 days)")
    before, after = planner.simulate_plan_impact("OS")
    print(f"Without reviewing today: {before:.2%} retention on exam day")
    print(f"If reviewed today:       {after:.2%} retention on exam day")

    section("8. AI DISAGREEMENT FEATURE")
    top_topic = ranked[0].topic
    print(f"Student says: 'I already know {top_topic} well, stop pushing it.'")
    event = engine.register_disagreement(
        topic=top_topic,
        student_claimed_confidence=90,
        reason="Feels confident after reviewing separately",
        override_days=3,
    )
    print(f"Disagreement logged: topic={event.topic}, claimed_confidence={event.student_claimed_confidence}, "
          f"expires={event.expires}")

    re_ranked = engine.rank_topics()
    new_score = next(r.priority_score for r in re_ranked if r.topic == top_topic)
    print(f"Priority score after override: {new_score:.3f} (was {ranked[0].priority_score:.3f})")

    print("\nNext quiz on this topic comes back WRONG:")
    print(engine.reconcile_disagreement(top_topic, next_quiz_correct=False))
    final_rank = engine.rank_topics()
    final_score = next(r.priority_score for r in final_rank if r.topic == top_topic)
    print(f"Priority score after reconciliation: {final_score:.3f}")


if __name__ == "__main__":
    main()
