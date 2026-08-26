import streamlit as st

st.set_page_config(page_title="Onboarding", layout="wide")
st.title("👋 Welcome to ExamPilot")
st.caption("Let's set up your Knowledge Twin before you start studying.")

st.markdown("---")

# --- Basic info ---
st.subheader("1️⃣ Tell us about yourself")
name = st.text_input("Your name", placeholder="e.g. Aditi")
exam_date = st.date_input("When is your exam?")

st.markdown("---")

# --- Subjects/topics ---
st.subheader("2️⃣ What topics are you preparing?")
st.caption("Add the topics you need to study, separated by commas.")
topics_input = st.text_input(
    "Topics",
    placeholder="e.g. Arrays, Trees, Graphs, DP, OS",
    value="Arrays, Trees, Graphs, DP, OS"
)
topics = [t.strip() for t in topics_input.split(",") if t.strip()]

st.markdown("---")

# --- Initial self-rated confidence ---
st.subheader("3️⃣ Rate your current confidence per topic")
st.caption("This seeds your Knowledge Twin before any quizzes happen.")

initial_confidence = {}
if topics:
    for topic in topics:
        initial_confidence[topic] = st.slider(
            f"{topic}", min_value=0, max_value=100, value=50, key=f"conf_{topic}"
        )
else:
    st.info("Add at least one topic above to continue.")

st.markdown("---")

# --- Submit ---
if st.button("🚀 Create My Knowledge Twin"):
    if not name:
        st.error("Please enter your name.")
    elif not topics:
        st.error("Please add at least one topic.")
    else:
        st.session_state.student_name = name
        st.session_state.exam_date = str(exam_date)
        st.session_state.topics = topics
        st.session_state.initial_confidence = initial_confidence
        st.session_state.onboarded = True
        st.success(f"Welcome, {name}! Your Knowledge Twin has been created.")
        st.balloons()
        st.info("Head to the **Dashboard** tab to see your Twin in action.")