import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_team_data
from nhlRestEffects.utils import get_team_logo_url
from nhlRestEffects.analysis import (
    add_rolling_metrics,
    summarize_back_to_backs,
    get_back_to_back_pairs
)

# ---------------------- PAGE SETUP ----------------------
st.set_page_config(page_title="NHL Team Statistics Since 2016", layout="wide")

@st.cache_data
def load_cached_data(path):
    return load_team_data(path)

# ---------------------- LOAD DATA ----------------------
DATA_PATH = "data/all_teams.csv"
df = load_cached_data(DATA_PATH)


# ---------------------- SIDEBAR FILTERS ----------------------
st.sidebar.header("Filters")

mode = st.sidebar.radio("Mode", ["Team", "League-wide"])
team_list = sorted(df["playerTeam"].unique())

if mode == "Team":
    selected_team = st.sidebar.selectbox("Select Team", team_list)
else:
    selected_team = None

# Season filter
season_options = ["All Seasons (2016–Present)"] + sorted(df["season_label"].unique())
selected_season = st.sidebar.selectbox("Select Season", season_options)

if selected_season != "All Seasons (2016–Present)":
    metric_mode = st.sidebar.radio(
        "Metric",
        ["Raw xGF/xGA", "Expected Goals Percentage (xG%)", "Actual vs Expected Goals"]
    )
else:
    st.sidebar.markdown(
        "<small style='color:gray;'>Metric selection available when viewing a single season.</small>",
        unsafe_allow_html=True
    )
    metric_mode = "Expected Goals Percentage (xG%)" 


rolling_window = st.sidebar.selectbox("Rolling Average", [1, 5, 10], index=0)
home_away = st.sidebar.radio("Home/Away Split", ["All Games", "Home Only", "Away Only"])


# ---------------------- FILTER DATA ----------------------
if mode == "Team":
    team_df = df[df["playerTeam"] == selected_team].copy()
else:
    team_df = df.copy()

if home_away == "Home Only":
    team_df = team_df[team_df["home_or_away"] == "HOME"]
elif home_away == "Away Only":
    team_df = team_df[team_df["home_or_away"] == "AWAY"]

if selected_season != "All Seasons (2016–Present)":
    team_df = team_df[team_df["season_label"] == selected_season]

team_df = team_df.reset_index(drop=True)
team_df["Game Number"] = team_df.index + 1
team_df["gameDate"] = team_df["gameDate"].dt.date

# Apply rolling metrics from the package
team_df = add_rolling_metrics(team_df, rolling_window)


# ---------------------- HEADER WITH LOGO ----------------------
if mode == "Team":
    logo_url = get_team_logo_url(selected_team)

    col1, col2 = st.columns([1, 10])
    with col1:
        st.image(logo_url, width=80)
    with col2:
        st.header(f"{selected_team} — {metric_mode}")
else:
    st.header("League-wide Back-to-Back Summary")


# ---------------------- DATA PREVIEW ----------------------
if mode == "Team":
    st.subheader("Data Preview")

    preview_cols = [
        "season_label", "opposingTeam", "gameDate",
        "xG%", "xGA","goalsFor","goalsAgainst","win",
        "days_rest","back_to_back","Game Number"
    ]

    preview_cols = [c for c in preview_cols if c in team_df.columns]
    st.dataframe(team_df[preview_cols].head(10))


# ---------------------- MAIN PLOT ----------------------
if mode == "Team" and selected_season != "All Seasons (2016–Present)":
    fig, ax = plt.subplots(figsize=(14, 7))
    x = team_df["Game Number"]

    if metric_mode == "Raw xGF/xGA":
        smoothing = max(rolling_window, 3)
        y1 = team_df["xGF"].rolling(smoothing).mean()
        y2 = team_df["xGA"].rolling(smoothing).mean()

        ax.plot(x, y1, label="xGF", linewidth=2.2, color="#1f77b4")
        ax.plot(x, y2, label="xGA", linewidth=2.2, color="#ff7f0e")
        ylabel = "Expected Goals (Smoothed)"

    elif metric_mode == "Expected Goals Percentage (xG%)":
        y = team_df["xG%_roll"] if rolling_window > 1 else team_df["xG%"]
        ax.plot(x, y, label="xG%", linewidth=2.5, color="#1f77b4")
        ylabel = "xG%"

        avg_xg_pct = y.mean()
        ax.axhline(avg_xg_pct, color="#1f77b4", linestyle="--", linewidth=1.5, alpha=0.6)
        ax.text(x.iloc[-1] + 0.3, avg_xg_pct, f"Avg {avg_xg_pct:.1f}%", color="#1f77b4", fontsize=11)

        ax2 = ax.twinx()
        goals = team_df["goalsFor"]
        colors = ["green" if w else "red" for w in team_df["win"]]
        ax2.scatter(x, goals, color=colors, s=40, edgecolor="black")
        ax2.set_ylabel("Goals For")

    else: # Actual vs Expected
        smoothing = max(rolling_window, 3)
        gf = team_df["goalsFor"].rolling(smoothing).mean()
        ga = team_df["goalsAgainst"].rolling(smoothing).mean()
        xgf = team_df["xGF"].rolling(smoothing).mean()

        ax.plot(x, gf, label="Goals For", linewidth=2)
        ax.plot(x, ga, label="Goals Against", linewidth=2, color="#ff7f0e")
        ax.fill_between(x, xgf - 0.25, xgf + 0.25, color="#2ca02c", alpha=0.25, label="xGF (band)")
        ax.plot(x, xgf, color="#2ca02c", linewidth=1.6, linestyle="--")
        ylabel = "Goals"

    ax.set_xlabel("Game Number")
    ax.set_ylabel(ylabel)
    ax.legend()
    st.pyplot(fig)


# ---------------------- BACK-TO-BACK SUMMARY ----------------------
st.header("Back-to-Back Performance Summary")

summary = summarize_back_to_backs(team_df)
if summary is None:
    st.warning("No back-to-back games found.")
else:
    st.dataframe(summary)


# ---------------------- FIRST vs SECOND GAME ----------------------
b2b_pairs = get_back_to_back_pairs(team_df)

if not b2b_pairs:
    st.warning("No full back-to-back sets detected.")
else:
    st.subheader("B2B Game 1 vs Game 2 Comparison")

    data = {
        "Game Type": [], "xGF": [], "xGA": [], "xG%": [], "Goals For": [], "Goals Against": []
    }

    for game1, game2 in b2b_pairs:
        data["Game Type"].append("B2B Game 1")
        data["xGF"].append(game1["xGF"])
        data["xGA"].append(game1["xGA"])
        data["xG%"].append(game1["xG%"])
        data["Goals For"].append(game1["goalsFor"])
        data["Goals Against"].append(game1["goalsAgainst"])

        data["Game Type"].append("B2B Game 2")
        data["xGF"].append(game2["xGF"])
        data["xGA"].append(game2["xGA"])
        data["xG%"].append(game2["xG%"])
        data["Goals For"].append(game2["goalsFor"])
        data["Goals Against"].append(game2["goalsAgainst"])

    compare_df = pd.DataFrame(data)
    st.dataframe(compare_df.groupby("Game Type").mean())

    fig2, ax2 = plt.subplots(figsize=(12, 6))
    compare_df.groupby("Game Type").mean()[["xGF","xGA","Goals For","Goals Against"]].plot(kind="bar", ax=ax2)
    st.pyplot(fig2)

st.markdown("📊 Data sourced from MoneyPuck.com — analyzed using the `nhlRestEffects` Python package.")
