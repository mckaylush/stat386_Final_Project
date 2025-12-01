import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

from nhlRestEffects.data_loader import load_goalie_data
from nhlRestEffects.utils import get_headshot_url
from nhlRestEffects.analysis import filter_goalie, summarize_goalie

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ---------------------- PDF EXPORT ----------------------
def export_pdf(goalie1, goalie2, metrics_df, chart_bytes):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 760, "Goalie Comparison Report")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, 740, f"{goalie1} vs {goalie2}")

    if chart_bytes:
        pdf.drawImage(ImageReader(chart_bytes), 80, 430, width=420, height=260)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, 400, "Stats:")

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


# ---------------------- FILTER DATA ----------------------
goalie1 = filter_goalie(df, goalie1_name, selected_season, "All")
goalie2 = filter_goalie(df, goalie2_name, selected_season, "All")

metrics_raw = pd.DataFrame({
    goalie1_name: summarize_goalie(goalie1),
    goalie2_name: summarize_goalie(goalie2)
}).T


# ---------------------- KEEP ONLY 3 SIMPLE METRICS ----------------------
column_map = {
    "sv%": "Save %",
    "xG_saved_diff": "Goals Saved Above Expected",
    "xG_diff": "Goals Saved Above Expected"
}

valid_cols = [c for c in metrics_raw.columns if c in column_map]
metrics_df = metrics_raw[valid_cols]
metrics_df = metrics_df.rename(columns={k:v for k,v in column_map.items() if k in metrics_df.columns})

# Force numeric values
metrics_df = metrics_df.apply(pd.to_numeric, errors="coerce")


# ---------------------- HEADER ----------------------
col1, col2 = st.columns(2)

with col1:
    st.image(get_headshot_url(goalie1["playerId"].iloc[0]), width=150)
    st.subheader(goalie1_name)

with col2:
    st.image(get_headshot_url(goalie2["playerId"].iloc[0]), width=150)
    st.subheader(goalie2_name)


# ---------------------- SUMMARY INSIGHT ----------------------
st.subheader("🧠 Summary Insight")

if metrics_df.shape[1] > 1:
    diffs = (metrics_df.iloc[0] - metrics_df.iloc[1]).abs()
    strongest_metric = diffs.idxmax()
    leader = metrics_df[strongest_metric].idxmax()
    st.success(f"**{leader}** has the biggest edge in **{strongest_metric}**.")
else:
    st.info("Not enough comparable stats for a meaningful summary.")


# ---------------------- CHART ----------------------
st.subheader("📊 Metric Comparison")

chart_bytes = None
numeric_df = metrics_df.select_dtypes(include=[np.number])

if numeric_df.empty:
    st.info("No numeric data available to plot.")
else:
    fig, ax = plt.subplots(figsize=(9, 5))
    numeric_df.plot(kind="barh", ax=ax)
    ax.grid(axis="x", alpha=0.3)
    ax.set_xlabel("Value")
    st.pyplot(fig)

    chart_bytes = BytesIO()
    fig.savefig(chart_bytes, format="png")
    chart_bytes.seek(0)


# ---------------------- TABLE ----------------------
st.subheader("📋 Detailed Stats")
st.dataframe(metrics_df.style.format("{:.3f}"))


# ---------------------- PDF DOWNLOAD ----------------------
if st.button("📥 Download PDF Report"):
    pdf_buffer = export_pdf(goalie1_name, goalie2_name, metrics_df, chart_bytes)
    st.download_button(
        label="Download PDF",
        data=pdf_buffer,
        file_name=f"{goalie1_name}_vs_{goalie2_name}.pdf",
        mime="application/pdf"
    )


st.caption("Data sourced from MoneyPuck.com — powered by nhlRestEffects.")
