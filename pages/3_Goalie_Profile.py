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
    if "season" in df.columns:
        df["season"] = df["season"].astype(str)
    return df


# ---------------------- PDF EXPORT ----------------------
def export_pdf(goalie1, goalie2, metrics_df, img_bytes):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 760, "Goalie Performance Comparison Report")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, 740, f"Primary Goalie: {goalie1}")
    pdf.drawString(40, 725, f"Comparison: {goalie2}")

    # Bar chart image
    pdf.drawImage(ImageReader(img_bytes), 80, 430, width=420, height=260)

    # Metric table
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, 400, "Metric Values:")

    pdf.setFont("Helvetica", 10)
    y = 380
    for idx, row in metrics_df.iterrows():
        pieces = []
        for col in metrics_df.columns:
            val = row[col]
            if isinstance(val, (float, int)):
                pieces.append(f"{col}: {val:.3f}")
            else:
                pieces.append(f"{col}: {val}")
        line = f"{idx}:  " + " | ".join(pieces)

        while len(line) > 95:
            pdf.drawString(40, y, line[:95])
            line = line[95:]
            y -= 14
        pdf.drawString(40, y, line)
        y -= 14

    pdf.save()
    buffer.seek(0)
    return buffer


# ---------------------- PAGE FUNCTION ----------------------
def goalie_profile_page():
    st.title("🥅 Goalie Skill Comparison")

    df = load_goalie_data()

    # ---------------------- SIDEBAR ----------------------
    st.sidebar.header("Filters")

    seasons = sorted(df["season"].unique())
    situations = sorted(df["situation"].unique())
    goalies = sorted(df["name"].unique())

    season_filter = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
    situation_filter = st.sidebar.selectbox("Situation", ["All"] + situations)

    goalie1 = st.sidebar.selectbox("Primary Goalie", goalies)
    goalie2 = st.sidebar.selectbox("Compare Against",
                                   [g for g in goalies if g != goalie1])

    # Apply global filters to base df (so league avg respects filters too)
    filtered_df = df.copy()
    if season_filter != "All Seasons":
        filtered_df = filtered_df[filtered_df["season"] == season_filter]
    if situation_filter != "All":
        filtered_df = filtered_df[filtered_df["situation"] == situation_filter]

    # ---------------------- METRIC EXTRACTOR ----------------------
    def extract_metrics(name: str):
        g = filtered_df[filtered_df["name"] == name].copy()
        if g.empty:
            return None

        # Overall save% uses xOnGoal as shot proxy (consistent with earlier)
        total_xOnGoal = g["xOnGoal"].sum()
        total_goals = g["goals"].sum()

        # Danger splits
        hd_shots, hd_goals = g["highDangerShots"].sum(), g["highDangerGoals"].sum()
        md_shots, md_goals = g["mediumDangerShots"].sum(), g["mediumDangerGoals"].sum()
        ld_shots, ld_goals = g["lowDangerShots"].sum(), g["lowDangerGoals"].sum()

        # Games played: sum max per season (avoid double-counting situations)
        games_per_season = g.groupby("season")["games_played"].max()
        games_total = games_per_season.sum() if not games_per_season.empty else 1

        save_pct = 1 - (total_goals / max(total_xOnGoal, 1))

        hd_sv = 1 - (hd_goals / max(hd_shots, 1))
        md_sv = 1 - (md_goals / max(md_shots, 1))
        ld_sv = 1 - (ld_goals / max(ld_shots, 1))

        gsax_game = (g["xGoals"].sum() - total_goals) / max(games_total, 1)

        return pd.Series({
            "Save %": save_pct,
            "High Danger Save %": hd_sv,
            "Medium Danger Save %": md_sv,
            "Low Danger Save %": ld_sv,
        })

    g1 = extract_metrics(goalie1)
    g2 = extract_metrics(goalie2)

    if g1 is None or g2 is None:
        st.warning("Not enough data for the selected filters.")
        return

    # ---------------------- LEAGUE AVERAGE (RESPECTS FILTERS) ----------------------
    total_xOnGoal_all = filtered_df["xOnGoal"].sum()
    total_goals_all = filtered_df["goals"].sum()

    hd_shots_all, hd_goals_all = (
        filtered_df["highDangerShots"].sum(),
        filtered_df["highDangerGoals"].sum(),
    )
    md_shots_all, md_goals_all = (
        filtered_df["mediumDangerShots"].sum(),
        filtered_df["mediumDangerGoals"].sum(),
    )
    ld_shots_all, ld_goals_all = (
        filtered_df["lowDangerShots"].sum(),
        filtered_df["lowDangerGoals"].sum(),
    )

    league_games = (
        filtered_df.groupby(["name", "season"])["games_played"].max().sum()
    )
    league_games = league_games if league_games > 0 else 1

    league_series = pd.Series({
        "Save %": 1 - (total_goals_all / max(total_xOnGoal_all, 1)),
        "High Danger Save %": 1 - (hd_goals_all / max(hd_shots_all, 1)),
        "Medium Danger Save %": 1 - (md_goals_all / max(md_shots_all, 1)),
        "Low Danger Save %": 1 - (ld_goals_all / max(ld_shots_all, 1)),
    })

    metrics_df = pd.DataFrame(
        [g1, g2, league_series],
        index=[goalie1, goalie2, "League Avg"]
    )

    # ---------------------- QUICK TEXT INSIGHT ----------------------
    st.subheader("🧠 Quick Insight")

    diff = (g1 - g2) * 100  # % difference for % metrics, scaled for readability
    # Only look at the four percentage metrics for "strength"
    perc_cols = ["Save %", "High Danger Save %", "Medium Danger Save %", "Low Danger Save %"]
    biggest = diff[perc_cols].abs().idxmax()

    if diff[biggest] > 0:
        st.success(
            f"**{goalie1}** leads most in **{biggest}** "
            f"(about **{diff[biggest]:.2f} percentage points** better)."
        )
    else:
        st.success(
            f"**{goalie2}** leads most in **{biggest}** "
            f"(about **{abs(diff[biggest]):.2f} percentage points** better)."
        )

    # ---------------------- HORIZONTAL BAR CHART ----------------------
    st.subheader("📊 Metric Comparison (Real Values)")

    # For plotting: convert save% columns to 0–100, leave GSAx/Game as-is
    plot_df = metrics_df.copy()
    pct_cols = ["Save %", "High Danger Save %", "Medium Danger Save %", "Low Danger Save %"]
    plot_df[pct_cols] = plot_df[pct_cols] * 100  # convert to %
    metrics_order = plot_df.columns

    fig, ax = plt.subplots(figsize=(10, 6))

    y = np.arange(len(metrics_order))
    h = 0.25

    ax.barh(y - h, plot_df.loc[goalie1, metrics_order], h, label=goalie1)
    ax.barh(y,     plot_df.loc[goalie2, metrics_order], h, label=goalie2)
    ax.barh(y + h, plot_df.loc["League Avg", metrics_order], h,
            label="League Avg", alpha=0.6)

    ax.set_yticks(y)
    ax.set_yticklabels(metrics_order)
    ax.set_xlabel("Save metrics in %")
    ax.grid(axis="x", alpha=0.3)
    ax.legend()

    st.pyplot(fig)

    # Save bar chart for PDF
    img_bytes = BytesIO()
    fig.savefig(img_bytes, format="png", bbox_inches="tight")
    img_bytes.seek(0)

    # ---------------------- METRICS TABLE ----------------------
    st.subheader("📋 Metrics Table")
    st.dataframe(metrics_df.style.format("{:.3f}"))

    # ---------------------- PDF DOWNLOAD ----------------------
    st.subheader("📄 Export Comparison Report")

    if st.button("📥 Download PDF Report"):
        pdf_buffer = export_pdf(goalie1, goalie2, metrics_df, img_bytes)
        st.download_button(
            "Download File",
            data=pdf_buffer,
            file_name=f"{goalie1}_vs_{goalie2}_comparison.pdf",
        )

    st.caption("Data sourced from MoneyPuck.com")
