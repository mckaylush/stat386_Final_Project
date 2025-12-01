import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import pi
from io import BytesIO

from nhlRestEffects.data_loader import load_goalie_data
from nhlRestEffects.utils import get_headshot_url
from nhlRestEffects.analysis import filter_goalie

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ---------------------- PDF EXPORT ----------------------
def export_pdf(goalie1, goalie2, metrics_df, img_bytes):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 760, "Goalie Performance Comparison Report")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, 740, f"Primary Goalie: {goalie1}")
    pdf.drawString(40, 725, f"Comparison: {goalie2}")

    pdf.drawImage(ImageReader(img_bytes), 80, 430, width=420, height=260)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, 400, "Metric Breakdown:")

    pdf.setFont("Helvetica", 10)
    y = 380
    for idx, row in metrics_df.iterrows():
        formatted = " | ".join([f"{col}: {val:.3f}" for col, val in row.items()])
        pdf.drawString(40, y, f"{idx}: {formatted}")
        y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer


# ---------------------- PAGE ----------------------
st.title("🥅 Goalie Skill Comparison")

@st.cache_data
def load_cached_goalies():
    return load_goalie_data()

df = load_cached_goalies()


# ---------------------- SIDEBAR ----------------------
st.sidebar.header("Filters")

seasons = sorted(df["season"].astype(str).unique())
situations = sorted(df["situation"].unique())
goalies = sorted(df["name"].unique())

selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
selected_situation = st.sidebar.selectbox("Situation", ["All"] + situations)

goalie1_name = st.sidebar.selectbox("Primary Goalie", goalies)
goalie2_name = st.sidebar.selectbox("Compare With", [g for g in goalies if g != goalie1_name])


# ---------------------- APPLY PACKAGE FILTER ----------------------
goalie1 = filter_goalie(df, goalie1_name, selected_season, selected_situation)
goalie2 = filter_goalie(df, goalie2_name, selected_season, selected_situation)


# ---------------------- METRIC ENGINE ----------------------
def compute_metrics(g):

    low = g["lowDangerShots"].sum()
    med = g["mediumDangerShots"].sum()
    high = g["highDangerShots"].sum()
    total_shots = low + med + high

    return pd.Series({
        "GSAx": (g["xGoals"].sum() - g["goals"].sum()) * -1,  # invert so higher = better
        "% High Danger Shots": 1 - (high / total_shots if total_shots > 0 else 0),
        "High Danger Save %": 1 - (g["highDangerGoals"].sum() / high if high > 0 else 0),
        "Rebound Control Score": 1 - (g["rebounds"].sum() / g["unblocked_shot_attempts"].sum()
                                     if g["unblocked_shot_attempts"].sum() > 0 else 0),
        "Freeze Rate": (g["freeze"].sum() / g["unblocked_shot_attempts"].sum()
                        if g["unblocked_shot_attempts"].sum() > 0 else 0),
        "Puck Handling Index": (
            (g["playContinuedInZone"].sum() + g["playContinuedOutsideZone"].sum()) /
            (g["playStopped"].sum() + g["playContinuedInZone"].sum() + g["playContinuedOutsideZone"].sum())
            if (
                g["playStopped"].sum() + 
                g["playContinuedInZone"].sum() + 
                g["playContinuedOutsideZone"].sum()
            ) > 0 else 0),
        "Minutes Per Game": (g["icetime"].sum() / g["games_played"].sum() / 60
                             if g["games_played"].sum() > 0 else 0),
    })


metrics_df = pd.DataFrame({
    goalie1_name: compute_metrics(goalie1),
    goalie2_name: compute_metrics(goalie2)
}).T


# ---------------------- HEADER ----------------------
col1, col2 = st.columns(2)
with col1:
    st.image(get_headshot_url(goalie1["playerId"].iloc[0]), width=150)
    st.subheader(goalie1_name)

with col2:
    st.image(get_headshot_url(goalie2["playerId"].iloc[0]), width=150)
    st.subheader(goalie2_name)


# ---------------------- RADAR CHART ----------------------
st.subheader("📈 Goalie Skill Radar Chart")

radar_df = (metrics_df - metrics_df.min()) / (metrics_df.max() - metrics_df.min())

categories = radar_df.columns.tolist()
N = len(categories)

angles = [n / float(N) * 2 * pi for n in range(N)]
angles += angles[:1]

fig = plt.figure(figsize=(6, 6))
ax = plt.subplot(111, polar=True)

for goalie in radar_df.index:
    values = radar_df.loc[goalie].tolist()
    values += values[:1]
    ax.plot(angles, values, linewidth=2, label=goalie)
    ax.fill(angles, values, alpha=0.15)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=9)
ax.set_yticks([])
ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15))

st.pyplot(fig)

# Save for PDF
pdf_img = BytesIO()
fig.savefig(pdf_img, format="png")
pdf_img.seek(0)


# ---------------------- SUMMARY ----------------------
leaderboard = metrics_df.idxmax()
strength = leaderboard.value_counts().idxmax()

st.success(f"🧠 **Key takeaway:** {strength} is the area where one goalie most clearly outperforms the other.")


# ---------------------- TABLE ----------------------
st.subheader("📋 Metric Comparison Table")
st.dataframe(metrics_df.style.format("{:.3f}"))


# ---------------------- EXPORT ----------------------
if st.button("📥 Generate PDF Report"):
    pdf_buffer = export_pdf(goalie1_name, goalie2_name, metrics_df, pdf_img)
    st.download_button(
        "Download PDF",
        data=pdf_buffer,
        file_name=f"{goalie1_name}_vs_{goalie2_name}.pdf"
    )


st.caption("Data sourced from MoneyPuck.com — powered by `nhlRestEffects` package.")
