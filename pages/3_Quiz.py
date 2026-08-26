import streamlit as st
from utils import api_client

st.set_page_config(page_title="Quiz", layout="wide")
st.title("📝 Quiz")

topic = st.selectbox("Choose a topic to quiz yourself on:", ["OS", "Trees", "DP", "Graphs", "Arrays"])
questions = api_client.fetch_quiz_questions(topic)

if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

answers = {}
for i, q in enumerate(questions):
    st.markdown(f"**Q{i+1}. {q['question']}**")
    options = ["— Select an answer —"] + q["options"]
    answers[i] = st.radio("Select one:", options, key=f"q{i}", label_visibility="collapsed")
    st.markdown("")

if st.button("Submit Quiz"):
    unanswered = [i for i, q in enumerate(questions) if answers[i] == "— Select an answer —"]
    if unanswered:
        st.error("Please answer all questions before submitting.")
    else:
        correct = sum(1 for i, q in enumerate(questions) if answers[i] == q["answer"])
        score_percent = round((correct / len(questions)) * 100)
        st.session_state.quiz_submitted = True
        st.session_state.last_score = score_percent
        st.session_state.last_topic = topic

if st.session_state.quiz_submitted:
    score = st.session_state.last_score
    t = st.session_state.last_topic
    st.markdown("---")
    st.subheader("Result")
    st.metric("Your Score", f"{score}%")

    new_confidence = api_client.submit_quiz_result(t, score)
    st.info(f"🤖 Twin updated: your confidence in **{t}** is now **{new_confidence}%**.")
    st.caption("(This updates in the mock data engine — Person 1's real Knowledge Twin will replace this logic.)")