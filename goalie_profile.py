import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_goalie_data(path="data/goalies_allseasons.csv"):
    df = pd.read_csv(path)
    df["season"] = df["season"].astype(str)
    return df


# ---------------------- PDF EXPORT ----------------------
def export_pdf(goalie1, goalie2, metrics_df, img_bytes):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 760, f"Goalie Comparison Report")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, 740, f"{goalie1} vs {goalie2}")

    pdf.drawImage(ImageReader(img_bytes), 80, 420, width=420, height=280)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, 390, "Metric Values:")

    y = 370
    pdf.setFont("Helvetica", 10)

    for row_name, row in metrics_df.iterrows():
        line = f"{row_name}:  " + " | ".join([f"{col}={row[col]:.3f}" for col in metrics_df.columns])

        while len(line) > 95:
            pdf.drawString(40, y, line[:95])
            line = line[95:]
            y -= 14

        pdf.drawString(40, y, line)
        y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer


# ---------------------- PAGE ----------------------
def goalie_profile_page():

    st.title("🥅 Goalie Skill Comparison")

    df = load_goalie_data()

    # ---- Sidebar Filters ----
    seasons = sorted(df["season"].unique())
    situations = sorted(df["situation"].unique())
    goalies = sorted(df["name"].unique())

    season_filter = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
    situation_filter = st.sidebar.selectbox("Situation", ["All"] + situations)

    goalie1 = st.sidebar.selectbox("Primary Goalie", goalies)
    goalie2 = st.sidebar.selectbox("Compare Against", [g for g in goalies if g != goalie1])

    # ---- Filter Function ----
    def extract_metrics(name):
        g = df[df["name"] == name].copy()

        if season_filter != "All Seasons":
            g = g[g["season"] == season_filter]
        if situation_filter != "All":
            g = g[g["situation"] == situation_filter]

        if g.empty:
            return None

        total_shots = g["unblocked_shot_attempts"].sum()
        total_goals = g["goals"].sum()

        hd_save = 1 - g["highDangerGoals"].sum() / max(g["highDangerShots"].sum(), 1)
        md_save = 1 - g["mediumDangerGoals"].sum() / max(g["mediumDangerShots"].sum(), 1)
        ld_save = 1 - g["lowDangerGoals"].sum() / max(g["lowDangerShots"].sum(), 1)

        save_pct = 1 - total_goals / max(total_shots, 1)
        gsax = (g["xGoals"].sum() - total_goals) / max(g["games_played"].max(), 1)

        return pd.Series({
            "Save %": save_pct,
            "High Danger Save %": hd_save,
            "Medium Danger Save %": md_save,
            "Low Danger Save %": ld_save,
            "GSAx/Game": gsax
        })

    g1 = extract_metrics(goalie1)
    g2 = extract_metrics(goalie2)

    if g1 is None or g2 is None:
        st.warning("Not enough data with selected filters.")
        return

    # ---- League Average ----
    league = extract_metrics(df["name"].unique()[0])  # temp init
    league = pd.Series({
        "Save %": 1 - df["goals"].sum() / df["unblocked_shot_attempts"].sum(),
        "High Danger Save %": 1 - df["highDangerGoals"].sum() / df["highDangerShots"].sum(),
        "Medium Danger Save %": 1 - df["mediumDangerGoals"].sum() / df["mediumDangerShots"].sum(),
        "Low Danger Save %": 1 - df["lowDangerGoals"].sum() / df["lowDangerShots"].sum(),
        "GSAx/Game": (df["xGoals"].sum() - df["goals"].sum()) / df["games_played"].max()
    })

    metrics_df = pd.DataFrame([g1, g2, league], index=[goalie1, goalie2, "League Avg"])

    # ---- Interpretation ----
    st.subheader("🧠 Quick Insight")

    diffs = (g1 - g2) * 100
    best_metric = diffs.abs().idxmax()

    if diffs[best_metric] > 0:
        st.success(f"🏒 **{goalie1}** leads most clearly in **{best_metric} (+{diffs[best_metric]:.2f}%)**.")
    else:
        st.success(f"🏒 **{goalie2}** leads most clearly in **{best_metric} ({diffs[best_metric]:.2f}%)**.")

    # ---- Bar Chart ----
    st.subheader("📊 Metrics Comparison")

    scaled = metrics_df.copy()
    scaled = (scaled - scaled.min()) / (scaled.max() - scaled.min()) * 100

    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(scaled.columns))
    height = 0.25

    ax.barh(y - height, scaled.loc[goalie1], height, label=goalie1)
    ax.barh(y, scaled.loc[goalie2], height, label=goalie2)
    ax.barh(y + height, scaled.loc["League Avg"], height, label="League Avg", alpha=0.6)

    ax.set_yticks(y)
    ax.set_yticklabels(scaled.columns)
    ax.grid(axis="x", alpha=0.3)
    ax.legend()

    st.pyplot(fig)

    # Save fig for PDF
    img_bytes = BytesIO()
    fig.savefig(img_bytes, format="png")
    img_bytes.seek(0)

    # ---- Metrics Table ----
    st.dataframe(metrics_df.style.format("{:.3f}"))

    # ---- Download PDF ----
    if st.button("📄 Download PDF Report"):
        pdf_buffer = export_pdf(goalie1, goalie2, metrics_df, img_bytes)
        st.download_button(
            "Download PDF",
            pdf_buffer,
            file_name=f"{goalie1}_vs_{goalie2}_comparison.pdf"
        )

    st.caption("Data sourced from MoneyPuck.com")
