import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

from nhlRestEffects.data_loader import load_goalie_data
from nhlRestEffects.utils import get_headshot_url
from nhlRestEffects.analysis import filter_goalie
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ---------------------- PAGE ----------------------
st.title("🥅 Goalie Comparison")

@st.cache_data
def load_cached_goalies():
    return load_goalie_data()

df = load_cached_goalies()


# ---------------------- SIDEBAR ----------------------
st.sidebar.header("Filters")

goalies = sorted(df["name"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
goalie1_name = st.sidebar.selectbox("Primary Goalie", goalies)
goalie2_name = st.sidebar.selectbox("Compare To", [g for g in goalies if g != goalie1_name])


# ---------------------- FILTER RAW DATA ----------------------
g1 = filter_goalie(df, goalie1_name, selected_season, "All")
g2 = filter_goalie(df, goalie2_name, selected_season, "All")


# ---------------------- COMPUTE METRICS ----------------------
def compute_metrics(g):
    high_shots = g["highDangerShots"].sum()
    high_goals = g["highDangerGoals"].sum()
    rebound_rate = g["rebounds"].sum() / g["unblocked_shot_attempts"].sum() if g["unblocked_shot_attempts"].sum() > 0 else None

    return {
        "Goals Saved Above Expected (GSAx)": g["flurryAdjustedxGoals"].sum() - g["goals"].sum(),
        "High Danger Save Rate": (1 - (high_goals / high_shots)) if high_shots > 0 else None,
        "Rebound Control Score": (1 - rebound_rate) if rebound_rate is not None else None,
    }

metrics_df = pd.DataFrame({
    goalie1_name: compute_metrics(g1),
    goalie2_name: compute_metrics(g2)
}).T


# ---------------------- HEADERS ----------------------
col1, col2 = st.columns(2)

with col1:
    st.image(get_headshot_url(g1["playerId"].iloc[0]), width=150)
    st.subheader(goalie1_name)

with col2:
    st.image(get_headshot_url(g2["playerId"].iloc[0]), width=150)
    st.subheader(goalie2_name)


# ---------------------- INSIGHT ----------------------
st.subheader("🧠 Summary Insight")

diffs = (metrics_df.iloc[0] - metrics_df.iloc[1]).abs()
top_metric = diffs.idxmax()
leader = metrics_df[top_metric].idxmax()

st.success(f"**{leader}** shows the strongest advantage in **{top_metric}**.")


# ---------------------- CHART ----------------------
st.subheader("📊 Comparison Chart")

numeric_df = metrics_df.apply(pd.to_numeric, errors="coerce")

fig, ax = plt.subplots(figsize=(9, 5))
numeric_df.plot(kind="barh", ax=ax)
ax.grid(axis="x", alpha=0.3)
ax.set_xlabel("Score")
st.pyplot(fig)

# Chart for PDF
chart_bytes = BytesIO()
fig.savefig(chart_bytes, format="png")
chart_bytes.seek(0)


# ---------------------- TABLE ----------------------
st.subheader("📋 Detailed Stats")
st.dataframe(metrics_df.style.format("{:.3f}"))


# ---------------------- PDF DOWNLOAD ----------------------
def export_pdf(goalie1, goalie2, metrics_df, chart):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 760, "Goalie Comparison Report")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, 740, f"{goalie1} vs {goalie2}")

    pdf.drawImage(ImageReader(chart), 80, 430, width=420, height=260)

    pdf.setFont("Helvetica", 10)
    y = 380
    for idx, row in metrics_df.iterrows():
        pdf.drawString(40, y, f"{idx}: " + " | ".join([f"{k} = {v:.3f}" for k, v in row.items()]))
        y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer

if st.button("📥 Download PDF Report"):
    pdf = export_pdf(goalie1_name, goalie2_name, metrics_df, chart_bytes)
    st.download_button("Download PDF", pdf, f"{goalie1_name}_vs_{goalie2_name}.pdf")


st.caption("Data sourced from MoneyPuck.com — powered by nhlRestEffects.")
