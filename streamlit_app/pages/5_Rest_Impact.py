import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data

st.title("⏱️ Rest Impact Analysis")

# ---------------------- LOAD & PREP DATA ----------------------
@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # 1) Parse dates – your CSV has string dates like "2016-10-12"
    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y-%m-%d", errors="coerce")

    # 2) Normalize team names (LA vs LAK, TB vs TBL, etc.)
    team_map = {
        "LA": "LAK", "L.A.": "LAK", "LOS": "LAK", "LOS ANGELES": "LAK",
        "TB": "TBL", "T.B.": "TBL", "TAM": "TBL", "TAMPA": "TBL",
    }
    df["playerTeam"] = (
        df["playerTeam"]
        .astype(str)
        .str.strip()
        .str.upper()
        .replace(team_map)
    )

    # 3) Expected goals percentage column
    # all_teams.csv has xGoalsPercentage
    df["xG"] = pd.to_numeric(df["xGoalsPercentage"], errors="coerce")

    # 4) Sort and compute days of rest
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # 5) Bin rest days into 0,1,2,3+
    #    We leave NaNs as NaN (first game for each team/season)
    df["rest_bucket"] = pd.cut(
        df["days_rest"],
        bins=[-0.5, 0.5, 1.5, 2.5, 100],   # (-0.5,0.5] => 0, (0.5,1.5] => 1, etc.
        labels=["0", "1", "2", "3+"]
    )

    return df


df = cached_rest_data()

# ---------------------- SIDEBAR FILTERS ----------------------
teams = sorted(df["playerTeam"].dropna().unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

# ---------------------- FILTERED DATA ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

# Drop rows with no rest info or no xG info
team_df = team_df.dropna(subset=["rest_bucket", "xG"])

# Debug counts so we can see if buckets make sense
st.caption(
    f"Rest bucket counts for {selected_team}"
    + (f" in {selected_season}" if selected_season != 'All Seasons' else "")
)
st.write(team_df["rest_bucket"].value_counts().sort_index())

# ---------------------- PLOT: xG% BY REST BUCKET ----------------------
st.subheader(f"📈 Expected Goals % vs Rest — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("⚠️ Not enough data for this team/season selection.")
else:
    summary = (
        team_df.groupby("rest_bucket")["xG"]
        .mean()
        .reindex(rest_order)
    )

    if summary.isna().all():
        st.warning("⚠️ No valid xG data to display for this selection.")
    else:
        summary = summary.fillna(0)

        fig, ax = plt.subplots(figsize=(10, 4))
        bars = ax.bar(rest_order, summary.values, color="#1f77b4", edgecolor="black")

        # Label bars with values
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
st.subheader("🏒 League Comparison: Fatigue Sensitivity")

# Use all teams; drop NaNs
league_df = df.dropna(subset=["rest_bucket", "xG"]).copy()

if league_df.empty:
    st.warning("No league-wide data available for fatigue ranking.")
else:
    league_summary = (
        league_df.groupby(["playerTeam", "rest_bucket"])["xG"]
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
