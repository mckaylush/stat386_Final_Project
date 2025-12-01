import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")

import os
st.write("📁 Current working directory:", os.getcwd())
st.write("📁 Available files:", os.listdir())

# ---------------------- LOAD & FIX DATA ----------------------
@st.cache_data
def load_data():
    df = load_rest_data("../data/all_teams.csv").copy()

    # ---- FIX DATES (CRITICAL STEP) ----
    df["gameDate"] = (
        df["gameDate"]
        .astype(str)
        .str.extract(r"(\d+)")[0]
        .str.zfill(8)
    )

    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d", errors="coerce")

    # ---- Clean team names (package method) ----
    df["playerTeam"] = df["playerTeam"].astype(str).apply(clean_team_abbrev)

    # ---- Expected Goals % column ----
    df["xG"] = pd.to_numeric(df.get("xGoalsPercentage", None), errors="coerce")

    # ---- Compute rest ----
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # ---- NEW NHL-style rest bucket logic ----
    def rest_bucket(days):
        if pd.isna(days): 
            return None  # exclude first game
        
        if days <= 1: 
            return "0"     # back-to-back
        
        if days == 2:
            return "1"     # one day rest
        
        if days == 3:
            return "2"     # two days rest
        
        return "3+"        # fully rested

    df["rest_bucket"] = df["days_rest"].apply(rest_bucket)

    # Remove unbucketed rows
    df = df.dropna(subset=["rest_bucket"])

    return df


df = load_data()


# ---------------------- Sidebar filters ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)


# ---------------------- Filter team view ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

team_df = team_df.dropna(subset=["xG"])


# ---------------------- Debug count ----------------------
st.caption(f"Rest bucket counts for {selected_team}")
st.write(team_df["rest_bucket"].value_counts().sort_index())


# ---------------------- Plot Expected Goals by Rest ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("Not enough data.")
else:
    summary = (
        team_df.groupby("rest_bucket")["xG"]
        .mean()
        .reindex(rest_order)
        .fillna(0)
    )

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(rest_order, summary.values, edgecolor="black")

    for label, value in zip(rest_order, summary.values):
        ax.text(label, value + 0.01, f"{value:.2f}", ha="center")

    ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.5)
    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    st.pyplot(fig)


# ---------------------- League-wide fatigue ranking ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking (League-wide)")

league_df = df.dropna(subset=["xG"])

if league_df.empty:
    st.warning("No league-wide data.")
else:
    league_summary = (
        league_df.groupby(["playerTeam", "rest_bucket"])["xG"]
        .mean()
        .unstack()
        .reindex(columns=rest_order)
        .fillna(0)
    )

    league_summary["Fatigue Impact (0 → 3+)"] = league_summary["3+"] - league_summary["0"]
    league_summary = league_summary.sort_values("Fatigue Impact (0 → 3+)")

    st.dataframe(league_summary.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
