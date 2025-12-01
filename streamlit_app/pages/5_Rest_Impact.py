import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # ---- FIX: Clean and parse dates correctly ----
    df["gameDate"] = (
        df["gameDate"]
        .astype(str)
        .str.extract(r"(\d+)")[0]     # keep only digits
        .str.zfill(8)                 # ensure YYYYMMDD format
    )

    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d", errors="coerce")

    # ---- Fix team names ----
    df["playerTeam"] = df["playerTeam"].astype(str).str.strip().str.upper()
    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)

    # ---- Use correct xG column ----
    possible_xg_cols = ["xGoalsPercentage","xG%","xGoalsPercent","xg_pct","expectedGoalsPct"]
    xg_col = next((c for c in possible_xg_cols if c in df.columns), None)
    df["xG"] = pd.to_numeric(df[xg_col], errors="coerce")

    # ---- Compute rest days ----
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # ---- Bucket rest days ----
    def assign_rest(days):
        if pd.isna(days): return "0"
        if days <= 0: return "0"
        if days == 1: return "1"
        if days == 2: return "2"
        return "3+"

    df["rest_bucket"] = df["days_rest"].apply(assign_rest)

    return df


df = cached_rest_data()

# Sidebar filters
teams = sorted(df["playerTeam"].dropna().unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

# Filter
team_df = df[df["playerTeam"] == selected_team].copy()
if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

team_df = team_df.dropna(subset=["xG", "rest_bucket"])
rest_order = ["0","1","2","3+"]

# Debug
st.caption(f"Rest bucket counts for {selected_team} ({selected_season})")
st.write(team_df["rest_bucket"].value_counts().sort_index())

# Plot
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

if team_df.empty:
    st.warning("⚠️ Not enough data for this team/season selection.")
else:
    summary = team_df.groupby("rest_bucket")["xG"].mean().reindex(rest_order).fillna(0)

    fig, ax = plt.subplots(figsize=(10,4))
    bars = ax.bar(rest_order, summary.values, edgecolor="black")

    for label, value in zip(rest_order, summary.values):
        ax.text(label, value + 0.01, f"{value:.2f}", ha="center")

    ax.axhline(summary.mean(), ls="--", color="red", alpha=0.5)
    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Level")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    st.pyplot(fig)

# League Ranking
st.subheader("📋 Fatigue Sensitivity Ranking (League-wide)")
league_df = df.dropna(subset=["xG", "rest_bucket"])

if league_df.empty:
    st.warning("No league-wide data available.")
else:
    league_summary = (
        league_df.groupby(["playerTeam","rest_bucket"])["xG"]
        .mean().unstack().reindex(columns=rest_order).fillna(0)
    )
    
    league_summary["Fatigue Impact (0 → 3+)"] = league_summary["3+"] - league_summary["0"]
    league_summary = league_summary.sort_values("Fatigue Impact (0 → 3+)")

    st.dataframe(league_summary.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Analysis powered by nhlRestEffects.")
