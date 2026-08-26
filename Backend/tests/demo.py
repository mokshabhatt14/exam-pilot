"""
demo.py

End-to-end demonstration of Person 4's pipeline: rank topics, build a study
plan, run the simulation mode, and exercise the AI disagreement feature.

Uses hand-built sample TopicKnowledgeState objects standing in for what
Person 1's Knowledge Twin Engine will eventually produce. Swap
`sample_states()` out for a real call into Person 1/2's code once it exists
-- nothing else in this file needs to change.
"""

from datetime import date, timedelta

from knowledge_state import TopicKnowledgeState
from prediction_engine import PredictionEngine
from study_planner import AdaptiveStudyPlanner


def sample_states(today: date):
    return [
        TopicKnowledgeState(
            topic_id="phy-101",
            subject="Physics",
            topic_name="Rotational Dynamics",
            confidence=0.55,
            ease_factor=1.8,
            repetitions=2,
            mistake_count=4,
            last_reviewed=today - timedelta(days=12),
            difficulty=4,
            exam_date=today + timedelta(days=6),
            quiz_history=[True, False, False, True, False],
            review_time_minutes=30,
        ),
        TopicKnowledgeState(
            topic_id="chem-204",
            subject="Chemistry",
            topic_name="Chemical Equilibrium",
            confidence=0.80,
            ease_factor=2.4,
            repetitions=5,
            mistake_count=1,
            last_reviewed=today - timedelta(days=2),
            difficulty=3,
            exam_date=today + timedelta(days=6),
            quiz_history=[True, True, True, False, True],
            review_time_minutes=20,
        ),
        TopicKnowledgeState(
            topic_id="math-310",
            subject="Math",
            topic_name="Differential Equations",
            confidence=0.35,
            ease_factor=1.5,
            repetitions=1,
            mistake_count=6,
            last_reviewed=today - timedelta(days=20),
            difficulty=5,
            exam_date=today + timedelta(days=2),
            quiz_history=[False, False, True, False],
            review_time_minutes=40,
        ),
        TopicKnowledgeState(
            topic_id="bio-150",
            subject="Biology",
            topic_name="Cell Respiration",
            confidence=0.90,
            ease_factor=2.6,
            repetitions=6,
            mistake_count=0,
            last_reviewed=today - timedelta(days=1),
            difficulty=2,
            exam_date=today + timedelta(days=15),
            quiz_history=[True, True, True, True],
            review_time_minutes=15,
        ),
    ]


def section(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    today = date(2026, 8, 26)
    states = sample_states(today)

    engine = PredictionEngine()
    planner = AdaptiveStudyPlanner(engine)

    section("1. RANKED TOPICS (forgetting-risk + urgency + difficulty)")
    ranked = engine.rank_topics(states, today)
    for r in ranked:
        print(f"\n[{r.priority_score:.3f}] {r.topic_name} ({r.subject})")
        print(f"   forgetting_risk={r.forgetting_risk}  exam_urgency={r.exam_urgency}  "
              f"difficulty={r.difficulty_score}  mistake_density={r.mistake_density}")
        print(f"   why: {r.explanation}")

    section("2. SANITY-CHECK EVALUATOR")
    warnings = engine.evaluate_predictions(ranked, states, today)
    print(warnings if warnings else "No issues found — output looks internally consistent.")

    section("3. WHAT SHOULD I STUDY RIGHT NOW? (top 2)")
    next_up = planner.what_to_study_next(states, today, session_size=2)
    for r in next_up:
        print(f"- {r.topic_name}: {r.explanation}")

    section("4. ADAPTIVE STUDY PLAN (60 minutes available today)")
    plan = planner.build_study_plan(states, today, total_minutes=60)
    for item in plan:
        print(f"- {item.allocated_minutes} min -> {item.topic_name} (priority {item.priority_score:.3f})")
    used = sum(i.allocated_minutes for i in plan)
    print(f"Total allocated: {used}/60 minutes")

    section("5. SIMULATION MODE — Differential Equations, next 5 days, no review")
    math_state = next(s for s in states if s.topic_id == "math-310")
    sim = planner.simulate_forgetting(math_state, today, days_ahead=5)
    for point in sim:
        bar = "#" * int(point.retention * 30)
        print(f"day {point.day_offset} ({point.calendar_date}): {point.retention:.2%} {bar}")

    section("6. EXAM-DAY OUTCOME IF NOTHING IS STUDIED FURTHER")
    outcomes = planner.simulate_exam_day_outcomes(states, today)
    for topic_id, (exam_date, retention) in outcomes.items():
        name = next(s.topic_name for s in states if s.topic_id == topic_id)
        print(f"- {name}: projected {retention:.2%} retention on exam day ({exam_date})")

    section("7. IMPACT OF STUDYING TODAY — Rotational Dynamics")
    phy_state = next(s for s in states if s.topic_id == "phy-101")
    before, after = planner.simulate_plan_impact(phy_state, today)
    print(f"Without reviewing today: {before:.2%} retention on exam day")
    print(f"If reviewed today:       {after:.2%} retention on exam day")

    section("8. AI DISAGREEMENT FEATURE")
    print("Student says: 'I already know Rotational Dynamics well, stop pushing it.'")
    event = engine.register_disagreement(
        state=phy_state,
        student_claimed_confidence=0.9,
        reason="Feels confident after reviewing textbook separately",
        as_of=today,
        override_days=3,
    )
    print(f"Disagreement logged: topic={event.topic_id}, claimed_confidence={event.student_claimed_confidence}, "
          f"expires={event.expires}")

    re_ranked = engine.rank_topics(states, today)
    new_score = next(r.priority_score for r in re_ranked if r.topic_id == "phy-101")
    print(f"Priority score after override: {new_score:.3f} (was {ranked[0].priority_score if ranked[0].topic_id=='phy-101' else '...'})")

    print("\nNext quiz on this topic comes back WRONG:")
    outcome_msg = engine.reconcile_disagreement(phy_state, next_quiz_correct=False)
    print(outcome_msg)
    final_rank = engine.rank_topics(states, today)
    final_score = next(r.priority_score for r in final_rank if r.topic_id == "phy-101")
    print(f"Priority score after reconciliation: {final_score:.3f}")


if __name__ == "__main__":
    main()
