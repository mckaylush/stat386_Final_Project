import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev
from nhlRestEffects.analysis import summarize_rest_buckets, rank_rest_sensitivity


# ---------------------- PAGE SETUP ----------------------
st.title("⏱️ Rest Impact Analysis")


# ---------------------- DATA LOAD & FIX ----------------------
@st.cache_data
def load_prepped_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Normalize team labels
    df["playerTeam"] = df["playerTeam"].astype(str).str.strip().str.upper()
    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)

    # Extract real date from gameId
    df["gameDate"] = df["gameId"].astype(str).str[:8]
    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d", errors="coerce")

    # Sort & compute days rest
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

# Convert rest values to integer (round nearest)
    df["days_rest"] = df["days_rest"].round().astype("Int64")
    
    def rest_bin(x):
        if pd.isna(x):
            return None
        if x <= 0:
            return "0"
        if x == 1:
            return "1"
        if x == 2:
            return "2"
        return "3+"
    
    df["rest_bin"] = df["days_rest"].apply(rest_bin)


    # Ensure numeric
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)
    df["xG%"] = pd.to_numeric(df["xG%"], errors="coerce")

    return df.dropna(subset=["rest_bin"])


df = load_prepped_data()


# ---------------------- SIDEBAR FILTERS ----------------------
st.sidebar.header("Filters")

teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Team", ["League-wide"] + teams)
selected_season = st.sidebar.selectbox("Season", ["All"] + seasons)


# ---------------------- APPLY FILTERS ----------------------
filtered_df = df.copy()

if selected_team != "League-wide":
    filtered_df = filtered_df[filtered_df["playerTeam"] == selected_team]

if selected_season != "All":
    filtered_df = filtered_df[filtered_df["season"].astype(str) == selected_season]


# ---------------------- CHART 1: REST vs xG% ----------------------
st.subheader("📈 Rest vs Expected Goals (xG%)")

summary = summarize_rest_buckets(filtered_df)

if summary.empty:
    st.warning("Not enough data to compare rest performance for this selection.")
else:
    # Sort bins in correct order
    order = ["0", "1", "2", "3+"]
    summary = summary.set_index("rest_bucket").reindex(order).reset_index()

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(summary["rest_bucket"], summary["xg_pct"], color="#1f77b4")
    ax.set_ylabel("xG%")
    ax.set_xlabel("Days of Rest")
    ax.set_title("Impact of Rest on Expected Performance")
    ax.grid(axis="y", alpha=0.3)

    st.pyplot(fig)


# ---------------------- CHART 2: WIN% VS REST ----------------------
st.subheader("🏒 Win Rate by Rest Day Category")

win_chart = filtered_df.groupby("rest_bin")["win"].mean().reset_index()

if win_chart.empty:
    st.warning("Not enough sample to compute win percentages.")
else:
    win_chart = win_chart.set_index("rest_bin").reindex(["0", "1", "2", "3+"]).reset_index()

    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.bar(win_chart["rest_bin"], win_chart["win"], color="#2ca02c")
    ax2.set_ylabel("Win %")
    ax2.set_xlabel("Days of Rest")
    ax2.set_title("Win Rate by Rest Recovery")
    ax2.grid(axis="y", alpha=0.3)

    st.pyplot(fig2)


# ---------------------- RANKING TABLE ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

ranking = rank_rest_sensitivity(filtered_df)

if ranking.empty:
    st.warning("Not enough sample size to compute fatigue scores.")
else:
    st.dataframe(ranking.style.format("{:.2f}"))


# ---------------------- FOOTER ----------------------
st.caption("Data sourced from MoneyPuck — processed using `nhlRestEffects`.")


