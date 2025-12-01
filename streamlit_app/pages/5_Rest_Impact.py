import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")

# ---------------------- LOAD & PREP DATA ----------------------
def load_and_prepare_rest_data():
    # Load from your CSV via the package
    df = load_rest_data("data/all_teams.csv").copy()

    # 1) Parse gameDate: values like 20151007 (YYYYMMDD)
    df["gameDate"] = pd.to_datetime(
        df["gameDate"].astype(str),
        format="%Y%m%d",
        errors="coerce"
    )

    # 2) Clean team abbreviations (handles LA/LAK, TB/TBL, etc.)
    df["playerTeam"] = df["playerTeam"].astype(str).str.strip()
    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)

    # 3) Expected goals % column (from your header: xGoalsPercentage)
    df["xG"] = pd.to_numeric(df["xGoalsPercentage"], errors="coerce")

    # 4) Sort and compute days of rest per team (x1 - previous game date x2)
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # 5) Bin rest days into 0, 1, 2, 3+  (leave NaN as NaN)
    def rest_bucket(days):
        if pd.isna(days):
            return np.nan
        if days <= 0:
            return "0"
        if days == 1:
            return "1"
        if days == 2:
            return "2"
        return "3+"

    df["rest_bucket"] = df["days_rest"].apply(rest_bucket)

    return df


# No cache so we don't fight stale data while fixing this
df = load_and_prepare_rest_data()

# ---------------------- SIDEBAR FILTERS ----------------------
teams = sorted(df["playerTeam"].dropna().unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

# ---------------------- FILTER DATA ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

# Drop rows without xG or rest bucket
team_df = team_df.dropna(subset=["xG", "rest_bucket"])

# ---------------------- DEBUG: SHOW REST BUCKET COUNTS ----------------------
st.caption(
    f"Rest bucket counts for {selected_team}"
    + (f" in {selected_season}" if selected_season != "All Seasons" else "")
)
st.write(team_df["rest_bucket"].value_counts().sort_index())

# ---------------------- PLOT: xG% BY REST ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("⚠️ Not enough data for this team/season selection.")
else:
    summary = (
        team_df
        .groupby("rest_bucket")["xG"]
        .mean()
        .reindex(rest_order)
    )

    if summary.isna().all():
        st.warning("⚠️ No valid xG data to display for this selection.")
    else:
        summary = summary.fillna(0)

        fig, ax = plt.subplots(figsize=(10, 4))
        bars = ax.bar(rest_order, summary.values, edgecolor="black")

        for x, height in zip(rest_order, summary.values):
            ax.text(x, height + 0.01, f"{height:.2f}", ha="center", fontsize=10)

        ax.set_ylabel("Avg Expected Goals %")
        ax.set_xlabel("Rest Days")

        title_suffix = (
            f"{selected_team} — {selected_season}"
            if selected_season != "All Seasons"
            else selected_team
        )
        ax.set_title(f"{title_suffix}: Expected Goals % by Rest Level")

        avg_line = summary.mean()
        ax.axhline(avg_line, linestyle="--", color="red", alpha=0.5)

        st.pyplot(fig)

# ---------------------- LEAGUE-WIDE FATIGUE RANKING ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking (League-wide)")

league_df = df.dropna(subset=["xG", "rest_bucket"]).copy()

if league_df.empty:
    st.warning("No league-wide data available for fatigue ranking.")
else:
    league_summary = (
        league_df
        .groupby(["playerTeam", "rest_bucket"])["xG"]
        .mean()
        .unstack("rest_bucket")
        .reindex(columns=rest_order)
        .fillna(0)
    )

    league_summary["Fatigue Impact (0 → 3+)"] = (
        league_summary["3+"] - league_summary["0"]
    )

    league_summary = league_summary.sort_values("Fatigue Impact (0 → 3+)")

    st.dataframe(league_summary.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Analysis powered by `nhlRestEffects`.")
