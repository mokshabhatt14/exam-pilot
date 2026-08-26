from utils import mock_data

# Flip this to False once the real backend is ready
USE_MOCK = True

def fetch_confidence_map():
    if USE_MOCK:
        return mock_data.get_confidence_map()
    # else: call real API, e.g.
    # response = requests.get("http://localhost:5000/api/confidence")
    # return response.json()

def fetch_predicted_tomorrow():
    if USE_MOCK:
        return mock_data.get_predicted_tomorrow()

def fetch_days_since_revised():
    if USE_MOCK:
        return mock_data.get_days_since_revised()

def fetch_recommendation():
    if USE_MOCK:
        return mock_data.get_recommendation()

def fetch_study_plan():
    if USE_MOCK:
        return mock_data.get_study_plan()

def fetch_quiz_questions(topic="OS"):
    if USE_MOCK:
        return mock_data.get_quiz_questions(topic)

def submit_quiz_result(topic, score_percent):
    if USE_MOCK:
        return mock_data.simulate_confidence_update(topic, score_percent)