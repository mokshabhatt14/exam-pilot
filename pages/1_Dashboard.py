import streamlit as st
import plotly.graph_objects as go
from utils import api_client

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Knowledge Twin Dashboard")

confidence = api_client.fetch_confidence_map()
predicted_drop = api_client.fetch_predicted_tomorrow()
days_since = api_client.fetch_days_since_revised()
rec = api_client.fetch_recommendation()

topics = list(confidence.keys())

# --- Current Confidence Map ---
st.subheader("🤖 Current Confidence Map")
for topic in topics:
    score = confidence[topic]
    st.write(f"**{topic}** — {score}%")
    st.progress(score / 100)

st.markdown("---")

# --- Today vs Tomorrow chart ---
st.subheader("📉 Predicted Confidence: Today vs Tomorrow")

today_scores = [confidence[t] for t in topics]
tomorrow_scores = [max(0, confidence[t] + predicted_drop[t]) for t in topics]

fig = go.Figure()
fig.add_trace(go.Bar(name="Today", x=topics, y=today_scores, marker_color="#4CAF50"))
fig.add_trace(go.Bar(name="Predicted Tomorrow", x=topics, y=tomorrow_scores, marker_color="#F44336"))
fig.update_layout(barmode="group", yaxis_title="Confidence %")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- Topic cards with trend + days since revised ---
st.subheader("🗂️ Topic Breakdown")
cols = st.columns(len(topics))
for i, topic in enumerate(topics):
    with cols[i]:
        st.markdown(f"**{topic}**")
        st.write(f"Confidence: {confidence[topic]}%")
        st.write(f"Last revised: {days_since[topic]}d ago")
        drop = predicted_drop[topic]
        arrows = "↓" * min(5, max(1, abs(drop) // 4))
        st.write(f"Trend: {arrows}")

st.markdown("---")

# --- Explanation panel ---
st.subheader("💡 Why This Recommendation?")
with st.expander(f"Twin recommends: **{rec['topic']}**"):
    for reason in rec["reasons"]:
        st.write(f"- {reason}")