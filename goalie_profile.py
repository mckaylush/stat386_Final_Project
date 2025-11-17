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


# ---------------------- NORMALIZATION FUNCTION ----------------------
def normalize(series):
    """Scales metric to 0–100 range for radar comparison."""
    if series.nunique() <= 1 or series.isna().all():
        return pd.Series([50] * len(series), index=series.index)
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
    pdf.drawImage(ImageReader(img_bytes), 90, 400, width=400, height=300)

    # Insert metric table
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 370, "Metric Values:")

    pdf.setFont("Helvetica", 10)
    y = 350

    for idx, row in metrics_df.iterrows():
        values = [f"{col}: {row[col]:.3f}" if isinstance(row[col], float) else f"{col}: {row[col]}"
                  for col in metrics_df.columns]

        text = f"{idx}:  " + "  |  ".join(values)

        # Wrap long lines
        while len(text) > 95:
            pdf.drawString(50, y, text[:95])
            text = text[95:]
            y -= 15

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

        # Aggregated values
        total_shots = g["unblocked_shot_attempts"].sum()
        total_exp_shots = g["xOnGoal"].sum()
        total_goals = g["goals"].sum()

        # Danger splits
        hd_shots, hd_goals = g["highDangerShots"].sum(), g["highDangerGoals"].sum()
        md_shots, md_goals = g["mediumDangerShots"].sum(), g["mediumDangerGoals"].sum()
        ld_shots, ld_goals = g["lowDangerShots"].sum(), g["lowDangerGoals"].sum()

        return pd.DataFrame({
            "Save % (Actual)": [1 - (total_goals / max(total_shots, 1))],
            "Save % (Expected)": [1 - (total_goals / max(total_exp_shots, 1))],
            "High Danger Save %": [1 - (hd_goals / max(hd_shots, 1))],
            "Medium Danger Save %": [1 - (md_goals / max(md_shots, 1))],
            "Low Danger Save %": [1 - (ld_goals / max(ld_shots, 1))],
            "GSAx/Game": [(g["xGoals"].sum() - g["goals"].sum()) / max(g["games_played"].max(), 1)]
        })



    g1 = filter_goalie(goalie1)
    g2 = filter_goalie(goalie2)

    if g1 is None or g2 is None:
        st.warning("Not enough data for selected filters.")
        return


    # ---------------------- LEAGUE AVERAGE BASELINE ----------------------
    team_avg = pd.DataFrame({
        "Save % (Actual)": [1 - (df["goals"].sum() / max(df["unblocked_shot_attempts"].sum(), 1))],
        "Save % (Expected)": [1 - (df["goals"].sum() / max(df["xOnGoal"].sum(), 1))],
        "High Danger Save %": [1 - (df["highDangerGoals"].sum() / max(df["highDangerShots"].sum(), 1))],
        "Medium Danger Save %": [1 - (df["mediumDangerGoals"].sum() / max(df["mediumDangerShots"].sum(), 1))],
        "Low Danger Save %": [1 - (df["lowDangerGoals"].sum() / max(df["lowDangerShots"].sum(), 1))],
        "GSAx/Game": [(df["xGoals"].sum() - df["goals"].sum()) / max(df["games_played"].max(), 1)]
    })


    # ---------------------- RADAR VISUAL ----------------------
    st.subheader("🕷️ Radar Skill Visualization")

    metrics = list(g1.columns)

    values_df = pd.concat([g1, g2, team_avg])
    normalized = values_df.apply(normalize)

    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    def plot(values, label, color):
        v = values.tolist() + [values.tolist()[0]]
        ax.plot(angles, v, label=label, linewidth=2, color=color)
        ax.fill(angles, v, alpha=0.25, color=color)

    plot(normalized.iloc[0], goalie1, "#1f77b4")
    plot(normalized.iloc[1], goalie2, "#d62728")
    plot(normalized.iloc[2], "League Avg", "#2ca02c")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics)
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png")
    img_buffer.seek(0)

    st.pyplot(fig)


    # ---------------------- TABLE ----------------------
    st.subheader("📋 Metrics Table")
    output_df = values_df.copy()
    output_df.index = [goalie1, goalie2, "League Avg"]
    st.dataframe(output_df.style.format("{:.3f}"))


    # ---------------------- PDF ----------------------
    st.subheader("📄 Export Comparison Report")

    if st.button("📥 Download PDF"):
        pdf_buffer = export_pdf(goalie1, goalie2, output_df, img_buffer)
        st.download_button("Download File", data=pdf_buffer, file_name=f"{goalie1}_vs_{goalie2}_report.pdf")


    st.caption("Data sourced from MoneyPuck.com")
