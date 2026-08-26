import streamlit as st
from utils import api_client

st.set_page_config(page_title="Study Plan", layout="wide")
st.title("📅 Today's Study Plan")

plan = api_client.fetch_study_plan()
rec = api_client.fetch_recommendation()

st.subheader("🤖 Twin-Prioritized Tasks")
for task in sorted(plan, key=lambda x: x["priority"]):
    with st.container(border=True):
        st.markdown(f"**#{task['priority']} — {task['topic']}**: {task['task']}")
        st.caption(f"⏱ {task['est_minutes']} min")

st.markdown("---")

# --- AI disagreement demo ---
st.subheader("🗣️ Ask the Twin")
student_choice = st.text_input("What do you want to study today?", placeholder="e.g. Machine Learning")

if student_choice:
    st.markdown("### 🤖 AI Twin says:")
    if student_choice.lower() not in [t.lower() for t in ["os", rec["topic"].lower()]]:
        st.warning(
            f"No. Your twin predicts you'll lose confidence in **{rec['topic']}** "
            f"by tomorrow if you skip it today.\n\n"
            f"Reasons:\n" + "\n".join([f"- {r}" for r in rec["reasons"]])
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ Fine, study {rec['topic']} first"):
                st.success(f"Great choice — {rec['topic']} added to top of your plan.")
        with col2:
            if st.button(f"➡️ Study {student_choice} anyway"):
                st.info(f"Okay, proceeding with {student_choice} — but the Twin will flag this risk again tomorrow.")
    else:
        st.success(f"Good call — {student_choice} is exactly what your Twin recommended.")