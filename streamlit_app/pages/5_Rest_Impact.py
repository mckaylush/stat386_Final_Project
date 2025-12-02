import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def load_data():
    try:
        df = load_rest_data("./data/all_teams.csv").copy()
    except Exception as e:
        st.error(f"❌ Could not load file: {e}")
        return pd.DataFrame()

    # --- Fix date format ---
    df["gameDate"] = (
        df["gameDate"]
        .astype(str)
        .str.extract(r"(\d{8})")[0]   # Ensure YYYYMMDD only
    )
    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d", errors="coerce")

    # --- Clean team names ---
    df["playerTeam"] = df["playerTeam"].astype(str).apply(clean_team_abbrev)

    # --- Use the correct xG metric already computed ---
    if "xG%" in df.columns:
        df["xG"] = pd.to_numeric(df["xG%"], errors="coerce")
    else:
        df["xG"] = pd.to_numeric(df.get("xGoalsPercentage"), errors="coerce")

    # --- Ensure key columns exist ---
    required_cols = ["playerTeam", "season", "rest_bucket", "xG", "gameDate"]
    df = df.dropna(subset=required_cols)

    return df


# ---------------------- LOAD DATA ----------------------
df = load_data()

st.write("📌 Debug: Rows Loaded:", len(df))


# ---------------------- SIDEBAR FILTERS ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)


# ---------------------- FILTER DATA ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

team_df = team_df.dropna(subset=["xG", "rest_bucket"])


# ---------------------- SHOW REST COUNTS ----------------------
st.caption(f"Rest bucket counts for {selected_team}")
st.write(team_df["rest_bucket"].value_counts().sort_index())


# ---------------------- PLOT REST EFFECT ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("⚠️ Not enough data.")
else:
    summary = (
        team_df.groupby("rest_bucket")["xG"]
        .mean()
        .reindex(rest_order)
        .fillna(0)
    )

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(rest_order, summary.values, edgecolor="black")

    for x, value in zip(rest_order, summary.values):
        ax.text(x, value + 0.5, f"{value:.2f}", ha="center")

    ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.5)
    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    st.pyplot(fig)


# ---------------------- LEAGUE RANKING ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

league_df = df.dropna(subset=["xG", "rest_bucket"]).copy()

if league_df.empty:
    st.warning("⚠️ No league-wide data available.")
else:
    league_summary = (
        league_df.groupby(["playerTeam", "rest_bucket"])["xG"]
        .mean()
        .unstack()
        .reindex(columns=rest_order)
        .fillna(0)
    )

    league_summary["Fatigue Impact (0→3+)"] = league_summary["3+"] - league_summary["0"]
    league_summary = league_summary.sort_values("Fatigue Impact (0→3+)")

    st.dataframe(league_summary.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
