import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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

    # ---------------------- APPLY FILTERS ----------------------
    def filter_goalie(name):
        g = df[df["name"] == name].copy()

        if season_filter != "All Seasons":
            g = g[g["season"] == season_filter]

        if situation_filter != "All":
            g = g[g["situation"] == situation_filter]

        if g.empty:
            return None

        # Compute key goalie performance metrics
        g["save_pct"] = 1 - (g["goals"] / g["xOnGoal"])
        g["GSAx"] = g["xGoals"] - g["goals"]
        g["highDangerSavePct"] = 1 - (g["highDangerGoals"] / g["highDangerShots"].replace(0, np.nan))
        g["mediumDangerSavePct"] = 1 - (g["mediumDangerGoals"] / g["mediumDangerShots"].replace(0, np.nan))
        g["lowDangerSavePct"] = 1 - (g["lowDangerGoals"] / g["lowDangerShots"].replace(0, np.nan))

        # Final aggregated metric row
        return pd.DataFrame({
            "Save %": [g["save_pct"].mean()],
            "High Danger Save %": [g["highDangerSavePct"].mean()],
            "Medium Danger Save %": [g["mediumDangerSavePct"].mean()],
            "Low Danger Save %": [g["lowDangerSavePct"].mean()],
            "GSAx per Game": [g["GSAx"].sum() / max(g["games_played"].max(), 1)]
        })

    g1 = filter_goalie(goalie1)
    g2 = filter_goalie(goalie2)

    if g1 is None or g2 is None:
        st.warning("Not enough data for selected filters.")
        return

    # ---------------------- RADAR CHART ----------------------
    st.subheader("🕷️ Radar Skill Visualization (Overlaid)")

    metrics = list(g1.columns)
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]  # loop back to start

    # Normalize for fair comparison
    combined = pd.concat([g1, g2])

    g1_values = normalize(g1.iloc[0]).tolist()
    g2_values = normalize(g2.iloc[0]).tolist()

    g1_values += g1_values[:1]
    g2_values += g2_values[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

    ax.plot(angles, g1_values, linewidth=2, label=goalie1, color="#1f77b4")
    ax.fill(angles, g1_values, alpha=0.25, color="#1f77b4")

    ax.plot(angles, g2_values, linewidth=2, label=goalie2, color="#d62728")
    ax.fill(angles, g2_values, alpha=0.25, color="#d62728")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_title("Skill Comparison Radar", fontsize=14, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))

    st.pyplot(fig)

    # ---------------------- RAW METRIC TABLE ----------------------
    st.subheader("📋 Raw Metrics")

    result_table = pd.DataFrame([g1.iloc[0], g2.iloc[0]], index=[goalie1, goalie2])
    st.dataframe(result_table.style.format("{:.3f}"))


    st.markdown("---")
    st.caption("Data source: MoneyPuck.com")


# ---------------------- END ----------------------
