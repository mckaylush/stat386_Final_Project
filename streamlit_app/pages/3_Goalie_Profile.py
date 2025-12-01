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


# ---------------------- DATA FILTER ----------------------
g1 = filter_goalie(df, goalie1_name, selected_season, "All")
g2 = filter_goalie(df, goalie2_name, selected_season, "All")


# ---------------------- METRIC ENGINE ----------------------
def calc_sv_rate(shots, goals):
    """Safe helper: returns a save % or None if no shots."""
    return (1 - (goals / shots)) if shots > 0 else None


def compute_metrics(g):
    low_shots, low_goals = g["lowDangerShots"].sum(), g["lowDangerGoals"].sum()
    med_shots, med_goals = g["mediumDangerShots"].sum(), g["mediumDangerGoals"].sum()
    high_shots, high_goals = g["highDangerShots"].sum(), g["highDangerGoals"].sum()

    rebound_rate = (
        g["rebounds"].sum() / g["unblocked_shot_attempts"].sum()
        if g["unblocked_shot_attempts"].sum() > 0 else None
    )

    return {
        "Low Danger SV%": calc_sv_rate(low_shots, low_goals),
        "Medium Danger SV%": calc_sv_rate(med_shots, med_goals),
        "High Danger SV%": calc_sv_rate(high_shots, high_goals),
        "Rebound Control Score": (1 - rebound_rate) if rebound_rate is not None else None,
    }


metrics_df = pd.DataFrame({
    goalie1_name: compute_metrics(g1),
    goalie2_name: compute_metrics(g2)
}).T

metrics_df = metrics_df.apply(pd.to_numeric, errors="coerce")


# ---------------------- HEADER ----------------------
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
best_metric = diffs.idxmax()
leader = metrics_df[best_metric].idxmax()

st.success(f"**{leader}** shows the strongest edge in **{best_metric}**.")


# ---------------------- CHART ----------------------
st.subheader("📊 Skill Comparison Chart")

fig, ax = plt.subplots(figsize=(9, 5))
metrics_df.plot(kind="barh", ax=ax)
ax.grid(axis="x", alpha=0.3)
ax.set_xlabel("Performance Score (Higher = Better)")
st.pyplot(fig)

chart_bytes = BytesIO()
fig.savefig(chart_bytes, format="png")
chart_bytes.seek(0)


# ---------------------- TABLE ----------------------
st.subheader("📋 Detailed Stats")
st.dataframe(metrics_df.style.format("{:.3f}"))


# ---------------------- PDF EXPORT ----------------------
def export_pdf(goalie1, goalie2, metrics_df, chart_bytes):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 760, "Goalie Comparison Report")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, 740, f"{goalie1} vs {goalie2}")

    pdf.drawImage(ImageReader(chart_bytes), 80, 430, width=420, height=260)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, 400, "Stats:")

    pdf.setFont("Helvetica", 10)
    y = 380
    for idx, row in metrics_df.iterrows():
        pdf.drawString(40, y, f"{idx}: " + " | ".join([f"{k}: {v:.3f}" for k, v in row.items()]))
        y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer


if st.button("📥 Download PDF Report"):
    pdf = export_pdf(goalie1_name, goalie2_name, metrics_df, chart_bytes)
    st.download_button("Download PDF", pdf, f"{goalie1_name}_vs_{goalie2_name}.pdf")


st.caption("Data sourced from MoneyPuck.com — powered by nhlRestEffects.")
