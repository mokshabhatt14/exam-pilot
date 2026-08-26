import random

def get_confidence_map():
    """Current confidence per topic (0-100)."""
    return {
        "Arrays": 98,
        "Trees": 62,
        "Graphs": 34,
        "DP": 21,
        "OS": 76,
    }

def get_predicted_tomorrow():
    """Predicted % drop in confidence by tomorrow if not revised."""
    return {
        "Arrays": -2,
        "Trees": -6,
        "Graphs": -12,
        "DP": -18,
        "OS": -4,
    }

def get_days_since_revised():
    return {
        "Arrays": 1,
        "Trees": 3,
        "Graphs": 5,
        "DP": 6,
        "OS": 6,
    }

def get_recommendation():
    """The Twin's top recommended topic + why."""
    return {
        "topic": "OS",
        "reasons": [
            "Confidence is 76%, but decaying fastest of all topics",
            "Not revised in 6 days",
            "High weight in upcoming exam",
        ],
    }

def get_study_plan():
    """Priority-ordered list of tasks for today."""
    return [
        {"topic": "OS", "task": "Revise Process Scheduling", "priority": 1, "est_minutes": 20},
        {"topic": "DP", "task": "Practice 5 DP problems", "priority": 2, "est_minutes": 30},
        {"topic": "Graphs", "task": "Watch BFS/DFS refresher", "priority": 3, "est_minutes": 15},
        {"topic": "Trees", "task": "Quick recap: Binary Search Trees", "priority": 4, "est_minutes": 10},
    ]

def get_quiz_questions(topic="OS"):
    """Sample quiz questions for a topic."""
    return [
        {
            "question": "Which scheduling algorithm can cause starvation?",
            "options": ["Round Robin", "Priority Scheduling", "FCFS", "SJF (non-preemptive)"],
            "answer": "Priority Scheduling",
        },
        {
            "question": "What does a context switch save?",
            "options": ["Only the PC", "Process state/registers", "Nothing", "Only memory"],
            "answer": "Process state/registers",
        },
        {
            "question": "Which is NOT a scheduling criterion?",
            "options": ["Throughput", "Turnaround time", "Screen resolution", "Waiting time"],
            "answer": "Screen resolution",
        },
    ]

def simulate_confidence_update(topic, score_percent):
    """
    Fake 'Twin update' logic: quiz score nudges confidence up/down.
    Person 1 will replace this with the real Knowledge Twin engine later.
    """
    current = get_confidence_map()
    old_score = current.get(topic, 50)
    delta = (score_percent - 50) / 5  # simple placeholder formula
    new_score = max(0, min(100, old_score + delta))
    return round(new_score, 1)