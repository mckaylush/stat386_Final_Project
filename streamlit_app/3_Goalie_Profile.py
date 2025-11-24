import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

# ---- Import packaged functions ----
from nhlRestEffects.data_loader import load_goalie_data
from nhlRestEffects.utils import get_headshot_url
from nhlRestEffects.analysis import filter_goalie, summarize_goalie

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
    pdf.drawString(40, 400, "Metric Values:")

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


# ---------------------- APPLY PACKAGE ANALYSIS ----------------------
goalie1 = filter_goalie(df, goalie1_name, selected_season, selected_situation)
goalie2 = filter_goalie(df, goalie2_name, selected_season, selected_situation)

metrics_df = pd.DataFrame(
    [summarize_goalie(goalie1), summarize_goalie(goalie2)],
    index=[goalie1_name, goalie2_name]
)


# ---------------------- HEADER DISPLAY ----------------------
col1, col2 = st.columns(2)
with col1:
    st.image(get_headshot_url(goalie1["playerId"].iloc[0]), width=150)
    st.subheader(goalie1_name)

with col2:
    st.image(get_headshot_url(goalie2["playerId"].iloc[0]), width=150)
    st.subheader(goalie2_name)


# ---------------------- INSIGHT ----------------------
st.subheader("🧠 Quick Insight")

diff = (metrics_df.loc[goalie1_name] - metrics_df.loc[goalie2_name])
biggest_metric = diff.abs().idxmax()

leader = goalie1_name if diff[biggest_metric] > 0 else goalie2_name
st.success(f"**{leader}** leads most in **{biggest_metric}**.")

# ---------------------- BAR CHART ----------------------
st.subheader("📊 Comparison Chart")

fig, ax = plt.subplots(figsize=(10, 6))
metrics_df.plot(kind="barh", ax=ax)
ax.grid(axis="x", alpha=0.3)
st.pyplot(fig)

# Save for PDF
pdf_img = BytesIO()
fig.savefig(pdf_img, format="png")
pdf_img.seek(0)


# ---------------------- TABLE ----------------------
st.subheader("📋 Stats Table")
st.dataframe(metrics_df.style.format("{:.3f}"))


# ---------------------- EXPORT ----------------------
if st.button("📥 Download PDF Report"):
    pdf_buffer = export_pdf(goalie1_name, goalie2_name, metrics_df, pdf_img)
    st.download_button(
        "Download PDF",
        data=pdf_buffer,
        file_name=f"{goalie1_name}_vs_{goalie2_name}.pdf"
    )


st.caption("Data sourced from MoneyPuck.com — powered by `nhlRestEffects` package.")