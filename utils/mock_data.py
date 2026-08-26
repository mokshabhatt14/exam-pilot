import random

DEFAULT_TOPICS = ["Arrays", "Trees", "Graphs", "DP", "OS"]

DEFAULT_CONFIDENCE = {
    "Arrays": 98,
    "Trees": 62,
    "Graphs": 34,
    "DP": 21,
    "OS": 76,
}

QUIZ_BANK = {
    "OS": [
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
    ],
    "DP": [
        {
            "question": "Dynamic Programming is mainly used to avoid what?",
            "options": ["Recursion", "Redundant subproblem computation", "Loops", "Recompiling"],
            "answer": "Redundant subproblem computation",
        },
        {
            "question": "Which technique stores results of subproblems?",
            "options": ["Memoization", "Sorting", "Hashing", "Compilation"],
            "answer": "Memoization",
        },
        {
            "question": "0/1 Knapsack is an example of which approach?",
            "options": ["Greedy", "Dynamic Programming", "Divide and Conquer", "Backtracking only"],
            "answer": "Dynamic Programming",
        },
    ],
    "Trees": [
        {
            "question": "In a Binary Search Tree, left child is always...",
            "options": ["Greater than parent", "Less than parent", "Equal to parent", "Random"],
            "answer": "Less than parent",
        },
        {
            "question": "Which traversal visits nodes in sorted order for a BST?",
            "options": ["Preorder", "Postorder", "Inorder", "Level order"],
            "answer": "Inorder",
        },
        {
            "question": "Height of a balanced binary tree with n nodes is approximately?",
            "options": ["O(n)", "O(log n)", "O(n^2)", "O(1)"],
            "answer": "O(log n)",
        },
    ],
    "Graphs": [
        {
            "question": "Which algorithm finds the shortest path in a weighted graph with no negative edges?",
            "options": ["DFS", "BFS", "Dijkstra's", "Bubble Sort"],
            "answer": "Dijkstra's",
        },
        {
            "question": "BFS uses which data structure internally?",
            "options": ["Stack", "Queue", "Heap", "Linked List"],
            "answer": "Queue",
        },
        {
            "question": "A graph with no cycles is called?",
            "options": ["Tree", "Acyclic", "Both Tree and Acyclic", "Directed"],
            "answer": "Both Tree and Acyclic",
        },
    ],
    "Arrays": [
        {
            "question": "What is the time complexity of accessing an element by index in an array?",
            "options": ["O(n)", "O(log n)", "O(1)", "O(n^2)"],
            "answer": "O(1)",
        },
        {
            "question": "Which algorithm is commonly used to search a sorted array efficiently?",
            "options": ["Linear Search", "Binary Search", "Bubble Sort", "DFS"],
            "answer": "Binary Search",
        },
        {
            "question": "Inserting an element at the beginning of an array is generally?",
            "options": ["O(1)", "O(log n)", "O(n)", "O(n^2)"],
            "answer": "O(n)",
        },
    ],
}


def get_generic_quiz_questions(topic):
    """Fallback quiz for any custom topic a student types during onboarding."""
    return [
        {
            "question": f"How confident do you feel about {topic} right now?",
            "options": ["Very confident", "Somewhat confident", "Not confident", "Never studied it"],
            "answer": "Very confident",
        },
        {
            "question": f"When did you last revise {topic}?",
            "options": ["Today", "This week", "Over a week ago", "Never"],
            "answer": "Today",
        },
        {
            "question": f"Have you solved practice problems on {topic}?",
            "options": ["Yes, many", "A few", "None yet", "Not applicable"],
            "answer": "Yes, many",
        },
    ]


def get_confidence_map():
    return DEFAULT_CONFIDENCE.copy()


def get_predicted_tomorrow():
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
    return {
        "topic": "OS",
        "reasons": [
            "Confidence is 76%, but decaying fastest of all topics",
            "Not revised in 6 days",
            "High weight in upcoming exam",
        ],
    }


def get_study_plan():
    return [
        {"topic": "OS", "task": "Revise Process Scheduling", "priority": 1, "est_minutes": 20},
        {"topic": "DP", "task": "Practice 5 DP problems", "priority": 2, "est_minutes": 30},
        {"topic": "Graphs", "task": "Watch BFS/DFS refresher", "priority": 3, "est_minutes": 15},
        {"topic": "Trees", "task": "Quick recap: Binary Search Trees", "priority": 4, "est_minutes": 10},
    ]


def get_quiz_questions(topic="OS"):
    return QUIZ_BANK.get(topic, get_generic_quiz_questions(topic))


def simulate_confidence_update(topic, score_percent, current_score=None):
    """Fake 'Twin update' logic: quiz score nudges confidence up/down."""
    old_score = current_score if current_score is not None else DEFAULT_CONFIDENCE.get(topic, 50)
    delta = (score_percent - 50) / 5
    new_score = max(0, min(100, old_score + delta))
    return round(new_score, 1)