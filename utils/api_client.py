import streamlit as st
from utils import mock_data

USE_MOCK = True


def _is_onboarded():
    return st.session_state.get("onboarded", False) and st.session_state.get("topics")


def fetch_confidence_map():
    if _is_onboarded():
        return dict(st.session_state.initial_confidence)
    return mock_data.get_confidence_map()


def fetch_predicted_tomorrow():
    if _is_onboarded():
        # No revision history yet right after onboarding, so estimate drop
        # as inversely proportional to confidence — lower confidence decays faster.
        confidence = st.session_state.initial_confidence
        return {
            topic: -max(1, round((100 - score) / 8))
            for topic, score in confidence.items()
        }
    return mock_data.get_predicted_tomorrow()


def fetch_days_since_revised():
    if _is_onboarded():
        # Just onboarded, so nothing has been revised yet.
        return {topic: 0 for topic in st.session_state.topics}
    return mock_data.get_days_since_revised()


def fetch_recommendation():
    if _is_onboarded():
        confidence = st.session_state.initial_confidence
        weakest_topic = min(confidence, key=confidence.get)
        return {
            "topic": weakest_topic,
            "reasons": [
                f"Confidence is only {confidence[weakest_topic]}% based on your self-rating",
                "No revision history yet since you just onboarded",
                "Lowest-rated topic is prioritized first",
            ],
        }
    return mock_data.get_recommendation()


def fetch_study_plan():
    if _is_onboarded():
        confidence = st.session_state.initial_confidence
        sorted_topics = sorted(confidence, key=confidence.get)
        plan = []
        for i, topic in enumerate(sorted_topics):
            est_minutes = 30 if confidence[topic] < 40 else (20 if confidence[topic] < 70 else 10)
            plan.append({
                "topic": topic,
                "task": f"Revise {topic} fundamentals",
                "priority": i + 1,
                "est_minutes": est_minutes,
            })
        return plan
    return mock_data.get_study_plan()


def fetch_quiz_questions(topic="OS"):
    return mock_data.get_quiz_questions(topic)


def fetch_available_topics():
    if _is_onboarded():
        return st.session_state.topics
    return mock_data.DEFAULT_TOPICS


def submit_quiz_result(topic, score_percent):
    current = fetch_confidence_map().get(topic)
    new_score = mock_data.simulate_confidence_update(topic, score_percent, current_score=current)
    if _is_onboarded():
        st.session_state.initial_confidence[topic] = new_score
    return new_score