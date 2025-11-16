import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_goalie_data(path="data/goalies_allseasons.csv"):
    df = pd.read_csv(path)

    if "season" in df.columns:
        df["season"] = df["season"].astype(str)

    return df


# ---------------------- NORMALIZATION FUNCTION ----------------------
def normalize(series):
    """Scales metric to 0–100 range for radar comparison."""
    if series.nunique() == 1:  # avoid division by zero
        return series * 0 + 50
    return (series - series.min()) / (series.max() - series.min()) * 100


# ---------------------- PDF EXPORT FUNCTION ----------------------
def export_pdf(goalie_name, comparison_name, metrics_df, img_bytes):

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 760, f"Goalie Performance Comparison Report")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 735, f"Primary Goalie: {goalie_name}")
    pdf.drawString(50, 720, f"Comparison: {comparison_name}")

    # Insert radar image
    pdf.drawImage(img_bytes, 90, 400, width=400, height=300)

    # Insert metric table
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 370, "Metric Values:")

    pdf.setFont("Helvetica", 10)

    y = 350
    for row in metrics_df.itertuples():
        text = f"{row.Index}:  " + "  |  ".join([f"{col}: {getattr(row, col):.3f}" for col in metrics_df.columns])
        pdf.drawString(50, y, text)
        y -= 15

    pdf.save()
    buffer.seek(0)

    return buffer


# ---------------------- PAGE FUNCTION ----------------------
def goalie_profile_page():

    st.title("🕸️ Goalie Skill Radar Comparison")

    df = load_goalie_data()

    # ---------------------- SIDEBAR ----------------------
    st.sidebar.header("Filters")

    seasons = sorted(df["season"].unique())
    situations = sorted(df["situation"].unique())
    goalies = sorted(df["name"].unique())

    season_filter = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
    situation_filter = st.sidebar.selectbox("Situation", ["All"] + situations)

    goalie1 = st.sidebar.selectbox("Primary Goalie", goalies)
    goalie2 = st.sidebar.selectbox("Compare Against", [g for g in goalies if g != goalie1])

    # ---------------------- FILTERING FUNCTION ----------------------
    def filter_goalie(name):
        g = df[df["name"] == name].copy()

        if season_filter != "All Seasons":
            g = g[g["season"] == season_filter]

        if situation_filter != "All":
            g = g[g["situation"] == situation_filter]

        if g.empty:
            return None

        # Performance metrics
        g["save_pct"] = 1 - (g["goals"] / g["xOnGoal"])
        g["GSAx"] = g["xGoals"] - g["goals"]
        g["highDangerSavePct"] = 1 - (g["highDangerGoals"] / g["highDangerShots"].replace(0, np.nan))
        g["mediumDangerSavePct"] = 1 - (g["mediumDangerGoals"] / g["mediumDangerShots"].replace(0, np.nan))
        g["lowDangerSavePct"] = 1 - (g["lowDangerGoals"] / g["lowDangerShots"].replace(0, np.nan))

        return pd.DataFrame({
            "Save %": [g["save_pct"].mean()],
            "High Danger Save %": [g["highDangerSavePct"].mean()],
            "Medium Danger Save %": [g["mediumDangerSavePct"].mean()],
            "Low Danger Save %": [g["lowDangerSavePct"].mean()],
            "GSAx/Game": [g["GSAx"].sum() / max(g["games_played"].max(), 1)]
        })

    g1 = filter_goalie(goalie1)
    g2 = filter_goalie(goalie2)

    if g1 is None or g2 is None:
        st.warning("Not enough data for selected filters.")
        return

    # ---------------------- TEAM AVERAGE BENCHMARK ----------------------
    team_avg = pd.DataFrame({
        "Save %": [df["goals"].sum() / df["xOnGoal"].sum()],
        "High Danger Save %": [(1 - df["highDangerGoals"].sum() / df["highDangerShots"].sum())],
        "Medium Danger Save %": [(1 - df["mediumDangerGoals"].sum() / df["mediumDangerShots"].sum())],
        "Low Danger Save %": [(1 - df["lowDangerGoals"].sum() / df["lowDangerShots"].sum())],
        "GSAx/Game": [(df["xGoals"].sum() - df["goals"].sum()) / (df["games_played"].max() * len(df["name"].unique()))]
    })

    # ---------------------- RADAR VISUAL ----------------------
    st.subheader("🕷️ Radar Skill Visualization")

    metrics = list(g1.columns)
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    combined = pd.concat([g1, g2, team_avg])

    values1 = normalize(g1.iloc[0]).tolist() + [normalize(g1.iloc[0]).tolist()[0]]
    values2 = normalize(g2.iloc[0]).tolist() + [normalize(g2.iloc[0]).tolist()[0]]
    values_avg = normalize(team_avg.iloc[0]).tolist() + [normalize(team_avg.iloc[0]).tolist()[0]]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    ax.plot(angles, values1, linewidth=2, label=goalie1, color="#1f77b4")
    ax.fill(angles, values1, alpha=0.25, color="#1f77b4")

    ax.plot(angles, values2, linewidth=2, label=goalie2, color="#d62728")
    ax.fill(angles, values2, alpha=0.25, color="#d62728")

    # Benchmark line
    ax.plot(angles, values_avg, linewidth=2, linestyle="--", label="NHL Avg", color="#2ca02c")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics)
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    # Save image bytes for PDF
    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png")
    img_buffer.seek(0)

    st.pyplot(fig)

    # ---------------------- METRIC TABLE ----------------------
    st.subheader("📋 Metrics Table")
    output_df = pd.concat([g1, g2, team_avg], axis=0)
    output_df.index = [goalie1, goalie2, "League Avg"]
    st.dataframe(output_df.style.format("{:.3f}"))

    # ---------------------- PDF DOWNLOAD ----------------------
    st.subheader("📄 Export Comparison Report")

    if st.button("📥 Download PDF"):
        pdf_buffer = export_pdf(goalie1, goalie2, output_df, img_buffer)
        st.download_button("Download File", data=pdf_buffer, file_name=f"{goalie1}_vs_{goalie2}_report.pdf")


    st.caption("Data sourced from MoneyPuck.com")
