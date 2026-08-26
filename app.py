import streamlit as st
from utils import api_client

st.set_page_config(page_title="ExamPilot", page_icon="🧠", layout="wide")

st.title("🧠 ExamPilot")
st.caption("Your AI Knowledge Twin — predicting what you'll forget before you do.")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("👤 You")
    st.metric("Overall Progress", "82%")
    st.write("Keep going — check the **Dashboard** tab to see your Knowledge Twin.")

with col2:
    st.subheader("🤖 Your AI Twin")
    confidence = api_client.fetch_confidence_map()
    avg_confidence = sum(confidence.values()) / len(confidence)
    st.metric("Twin's Confidence in You", f"{avg_confidence:.0f}%")
    rec = api_client.fetch_recommendation()
    st.info(f"💡 Twin recommends studying **{rec['topic']}** next.")

st.markdown("---")
st.markdown("Use the sidebar to explore: **Dashboard**, **Study Plan**, and **Quiz**.")