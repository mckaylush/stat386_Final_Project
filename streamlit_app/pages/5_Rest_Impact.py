import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def load_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # --- Fix team names early (LA vs LAK, TB vs TBL, etc.) ---
    df["playerTeam"] = df["playerTeam"].astype(str).apply(clean_team_abbrev)

    # Ensure xG exists
    if "xG%" in df.columns:
        df["xG"] = df["xG%"]
    elif "xGoalsPercentage" in df.columns:
        df["xG"] = df["xGoalsPercentage"]
    else:
        st.error("❌ No xG column available.")
        return pd.DataFrame()

    # Ensure valid numeric type
    df["xG"] = pd.to_numeric(df["xG"], errors="coerce")

    # Drop rows without rest bucket or xG
    df = df.dropna(subset=["rest_bucket", "xG"])

    return df


df = load_data()

if df.empty:
    st.error("❌ Dataset loaded, but contains no usable data.")
    st.stop()

# ---------------------- Sidebar Filters ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

# ---------------------- Filter Data ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

team_df = team_df.dropna(subset=["xG"])

# ---------------------- Rest bucket summary ----------------------
rest_order = ["0", "1", "2", "3+"]

st.caption(f"Rest bucket counts for {selected_team} ({selected_season})")
st.write(team_df["rest_bucket"].value_counts().sort_index())

# ---------------------- League avg for reference line ----------------------
league_avg = df["xG"].mean()

# ---------------------- Plot ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

if team_df.empty:
    st.warning("⚠️ Not enough data for this team and season.")
else:
    summary = (
        team_df.groupby("rest_bucket")["xG"]
        .mean()
        .reindex(rest_order)
        .fillna(0)
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(rest_order, summary.values, color="#1f77b4", edgecolor="black")

    # Annotate values properly on bars
    for x, height in zip(rest_order, summary.values):
        ax.text(x, height + 0.005, f"{height:.2f}", ha="center", fontsize=11)

    # Team average line
    ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.6, label="Team Avg")

    # League average line
    ax.axhline(league_avg, linestyle="--", color="gray", alpha=0.6, label="League Avg")

    ax.set_ylabel("Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    ax.legend()
    st.pyplot(fig)

# ---------------------- League-wide ranking ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

league_df = df.copy()

league_summary = (
    league_df.groupby(["playerTeam", "rest_bucket"])["xG"]
    .mean()
    .unstack("rest_bucket")
    .reindex(columns=rest_order)
    .fillna(0)
)

league_summary["Fatigue Impact (0 → 3+)"] = league_summary["3+"] - league_summary["0"]
league_summary = league_summary.sort_values("Fatigue Impact (0 → 3+)", ascending=True)

st.dataframe(league_summary.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
