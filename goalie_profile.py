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


# ---------------------- PDF EXPORT FUNCTION ----------------------
def export_pdf(goalie_name, comparison_name, metrics_df, img_bytes):

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 760, "Goalie Performance Comparison Report")

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
        row_values = []
        for col in metrics_df.columns:
            val = row[col]
            if isinstance(val, float):
                row_values.append(f"{col}: {val:.3f}")
            else:
                row_values.append(f"{col}: {val}")

        text = f"{idx}:  " + "  |  ".join(row_values)

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
    def filter_goalie(name: str):
        g = df[df["name"] == name].copy()

        if season_filter != "All Seasons":
            g = g[g["season"] == season_filter]

        if situation_filter != "All":
            g = g[g["situation"] == situation_filter]

        if g.empty:
            return None

        # Aggregated totals
        total_shots = g["unblocked_shot_attempts"].sum()
        total_exp_shots = g["xOnGoal"].sum()
        total_goals = g["goals"].sum()

        hd_shots, hd_goals = g["highDangerShots"].sum(), g["highDangerGoals"].sum()
        md_shots, md_goals = g["mediumDangerShots"].sum(), g["mediumDangerGoals"].sum()
        ld_shots, ld_goals = g["lowDangerShots"].sum(), g["lowDangerGoals"].sum()

        games_played = max(g["games_played"].max(), 1)

        # Metrics (all in 0–1 scale here)
        save_pct_actual = 1 - (total_goals / max(total_shots, 1))
        save_pct_expected = 1 - (total_goals / max(total_exp_shots, 1))

        high_danger_sv = 1 - (hd_goals / max(hd_shots, 1))
        medium_danger_sv = 1 - (md_goals / max(md_shots, 1))
        low_danger_sv = 1 - (ld_goals / max(ld_shots, 1))

        gsax_game = (g["xGoals"].sum() - g["goals"].sum()) / games_played

        return pd.DataFrame({
            "Save %": [save_pct_actual],
            "High Danger Save %": [high_danger_sv],
            "Medium Danger Save %": [medium_danger_sv],
            "Low Danger Save %": [low_danger_sv],
            "GSAx/Game": [gsax_game],
        })

    g1 = filter_goalie(goalie1)
    g2 = filter_goalie(goalie2)

    if g1 is None or g2 is None:
        st.warning("Not enough data for selected filters.")
        return

    # ---------------------- LEAGUE AVERAGE BASELINE ----------------------
    total_shots_all = df["unblocked_shot_attempts"].sum()
    total_goals_all = df["goals"].sum()

    hd_shots_all, hd_goals_all = df["highDangerShots"].sum(), df["highDangerGoals"].sum()
    md_shots_all, md_goals_all = df["mediumDangerShots"].sum(), df["mediumDangerGoals"].sum()
    ld_shots_all, ld_goals_all = df["lowDangerShots"].sum(), df["lowDangerGoals"].sum()

    league_games_per_goalie = max(df["games_played"].max(), 1)

    league_save_pct = 1 - (total_goals_all / max(total_shots_all, 1))
    league_hd_sv = 1 - (hd_goals_all / max(hd_shots_all, 1))
    league_md_sv = 1 - (md_goals_all / max(md_shots_all, 1))
    league_ld_sv = 1 - (ld_goals_all / max(ld_shots_all, 1))
    league_gsax_game = (df["xGoals"].sum() - df["goals"].sum()) / league_games_per_goalie

    team_avg = pd.DataFrame({
        "Save %": [league_save_pct],
        "High Danger Save %": [league_hd_sv],
        "Medium Danger Save %": [league_md_sv],
        "Low Danger Save %": [league_ld_sv],
        "GSAx/Game": [league_gsax_game],
    })

    # ---------------------- RADAR VISUAL (SAVE% ONLY) ----------------------
    st.subheader("🕷️ Radar Skill Visualization")

    # Only use the four save% metrics for the radar
    radar_metrics = ["Save %", "High Danger Save %", "Medium Danger Save %", "Low Danger Save %"]

    # Build plotting DF and convert to percentage scale
    values_df = pd.concat([g1, g2, team_avg])
    radar_df = values_df[radar_metrics].copy() * 100  # 0–1 -> 0–100%

    angles = np.linspace(0, 2 * np.pi, len(radar_metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    def plot_one(row, label, color):
        vals = row.tolist() + [row.tolist()[0]]
        ax.plot(angles, vals, label=label, linewidth=2, color=color)
        ax.fill(angles, vals, alpha=0.25, color=color)

    plot_one(radar_df.iloc[0], goalie1, "#1f77b4")
    plot_one(radar_df.iloc[1], goalie2, "#d62728")
    plot_one(radar_df.iloc[2], "League Avg", "#2ca02c")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(radar_metrics)
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png")
    img_buffer.seek(0)

    st.pyplot(fig)

    # ---------------------- INTERPRETATION SECTION ----------------------
    st.subheader("🧠 Automated Interpretation")

    def generate_insight(name, row, league):
        text = f"**{name}:**\n"
        diffs = (row - league) * 100  # convert to %
        
        strength = diffs.sort_values(ascending=False)

        best = strength.index[0]
        worst = strength.index[-1]

        text += f"- Best category: **{best} (+{strength[best]:.2f}% vs league)**\n"
        text += f"- Weakest category: **{worst} ({strength[worst]:.2f}% vs league)**\n\n"

        return text


    league_row = radar_df.iloc[2]

    insight_text = ""

    insight_text += generate_insight(goalie1, radar_df.iloc[0], league_row)
    insight_text += generate_insight(goalie2, radar_df.iloc[1], league_row)

    # Comparison sentence
    diff = (radar_df.iloc[0] - radar_df.iloc[1]).mean()

    if abs(diff) < 1:
        comparison = "These goalies perform **very similarly overall.**"
    elif diff > 0:
        comparison = f"**{goalie1}** shows slightly stronger overall consistency compared to **{goalie2}.**"
    else:
        comparison = f"**{goalie2}** demonstrates slightly stronger performance trends than **{goalie1}.**"

    st.write(insight_text)
    st.info(comparison)

    # ---------------------- HORIZONTAL BAR COMPARISON ----------------------
    st.subheader("📊 Side-by-Side Metric Comparison")

    comparison_df = radar_df.copy()

    # Convert to 0–100 scale for cleaner visualization
    bar_df = comparison_df.copy() * 100
    bar_df.columns = [col + " (%)" for col in bar_df.columns]

    fig_bar, ax_bar = plt.subplots(figsize=(10, 6))

    y_positions = np.arange(len(bar_df.columns))
    height = 0.25  # spacing of bars

    ax_bar.barh(y_positions - height, bar_df.iloc[0], height, label=goalie1, color="#1f77b4", alpha=0.8)
    ax_bar.barh(y_positions, bar_df.iloc[1], height, label=goalie2, color="#d62728", alpha=0.8)
    ax_bar.barh(y_positions + height, bar_df.iloc[2], height, label="League Avg", color="#2ca02c", alpha=0.6)

    ax_bar.set_yticks(y_positions)
    ax_bar.set_yticklabels(bar_df.columns)
    ax_bar.set_xlabel("Performance (Scaled 0-100)")
    ax_bar.set_title("Metric-by-Metric Performance Comparison")
    ax_bar.grid(axis="x", alpha=0.3)
    ax_bar.legend()

    st.pyplot(fig_bar)


    # ---------------------- METRICS TABLE ----------------------
    st.subheader("📋 Metrics Table")

    output_df = values_df.copy()
    output_df.index = [goalie1, goalie2, "League Avg"]
    st.dataframe(output_df.style.format("{:.3f}"))

    # ---------------------- PDF EXPORT ----------------------
    st.subheader("📄 Export Comparison Report")

    if st.button("📥 Download PDF"):
        pdf_buffer = export_pdf(goalie1, goalie2, output_df, img_buffer)
        st.download_button(
            "Download File",
            data=pdf_buffer,
            file_name=f"{goalie1}_vs_{goalie2}_report.pdf",
        )

    st.caption("Data sourced from MoneyPuck.com")
