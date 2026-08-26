"""
demo.py

Run this to see the Knowledge Twin in action end-to-end — this reproduces
the exact kind of output your pitch describes, so you can screen-record it
for the judges or paste the output into your slides.

Usage:
    python demo.py
"""

from datetime import datetime, timedelta
from knowledge_twin_engine import KnowledgeTwinEngine


def line():
    print("-" * 60)


def main():
    topics = ["Arrays", "Trees", "Graphs", "DP", "OS"]
    exam_weights = {"Arrays": 0.8, "Trees": 1.0, "Graphs": 1.2, "DP": 1.3, "OS": 0.9}

    twin = KnowledgeTwinEngine(topics, exam_weights)

    print("Simulating a week of study activity...")
    line()

    # Day -6: studied Arrays heavily, did well
    six_days_ago = datetime.now() - timedelta(days=6)
    twin.record_action("Arrays", "studied", at_time=six_days_ago)
    twin.record_action("Arrays", "quiz", quiz_score=95, at_time=six_days_ago)

    # Day -5: revised Trees, okay quiz
    five_days_ago = datetime.now() - timedelta(days=5)
    twin.record_action("Trees", "revision", at_time=five_days_ago)
    twin.record_action("Trees", "quiz", quiz_score=70, at_time=five_days_ago)

    # Day -4: skipped Graphs entirely
    four_days_ago = datetime.now() - timedelta(days=4)
    twin.record_action("Graphs", "skipped", at_time=four_days_ago)

    # Day -6 (also): studied DP once, low quiz score, then never touched again
    twin.record_action("DP", "studied", at_time=six_days_ago)
    twin.record_action("DP", "quiz", quiz_score=58, at_time=six_days_ago)

    # Day -2: studied OS, made a mistake on a practice problem
    two_days_ago = datetime.now() - timedelta(days=2)
    twin.record_action("OS", "studied", at_time=two_days_ago)
    twin.record_action("OS", "mistake", at_time=two_days_ago)

    print("\n>>> CURRENT KNOWLEDGE TWIN STATE (right now)")
    line()
    for topic, conf in twin.get_confidence_map().items():
        bar = "#" * int(conf / 5)
        print(f"{topic:<10} {bar:<20} {conf:>5.1f}%")

    print("\n>>> PREDICTED STATE (24 hours from now, if the student does nothing)")
    line()
    predicted = twin.predict_confidence_map(hours_ahead=24)
    for topic, conf in predicted.items():
        bar = "#" * int(conf / 5)
        print(f"{topic:<10} {bar:<20} {conf:>5.1f}%")

    print("\n>>> FORGETTING RISK (predicted drop over next 24h)")
    line()
    risk = twin.get_forgetting_risk_map(hours_ahead=24)
    for topic, drop in sorted(risk.items(), key=lambda kv: -kv[1]):
        print(f"{topic:<10} -{drop:.1f}%")

    print("\n>>> AI TWIN RECOMMENDATION")
    line()
    recommended = twin.recommend_next_topic(hours_ahead=24)
    print(f"Recommended next topic: {recommended}\n")
    print(twin.explain(recommended, hours_ahead=24))

    print("\n>>> THE 'AI ARGUES WITH THE STUDENT' MOMENT")
    line()
    print('Student: "I want to study Machine Learning today."')
    print(f"AI Twin: \"No. {twin.explain(recommended, hours_ahead=24)}\"")


if __name__ == "__main__":
    main()
