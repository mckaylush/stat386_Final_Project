import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev
from nhlRestEffects.analysis import rank_rest_sensitivity

st.title("⏱️ Rest Impact Analysis")


# ---------------------- Load & Preprocess ----------------------
@st.cache_data
def load_prepped_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Normalize team names
    df["playerTeam"] = df["playerTeam"].astype(str).str.strip().str.upper()
    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)

    # Ensure game date is datetime
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")
    df = df.sort_values(["playerTeam", "gameDate"])

    # Compute rest BEFORE user filtering
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Create rest buckets matching your original version
    def rest_bin(x):
        if pd.isna(x):
            return None
        if x >= 5:
            return "5+"
        return str(int(x))

    df["rest_bin"] = df["days_rest"].apply(rest_bin)

    # Make sure key stats are numeric
    df["xG%"] = pd.to_numeric(df["xG%"], errors="coerce")
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    return df.dropna(subset=["rest_bin"])


df = load_prepped_data()

st.write("📅 Unique Dates:", df["gameDate"].head(20))
st.write(df[["playerTeam", "gameDate"]].head(10))

# ---------------------- Sidebar Filters ----------------------
st.sidebar.header("Filters")

teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].unique())

selected_team = st.sidebar.selectbox("Team", ["All Teams"] + teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + [str(s) for s in seasons])


# ---------------------- Apply Filtering AFTER rest computed ----------------------
filtered_df = df.copy()

if selected_team != "All Teams":
    filtered_df = filtered_df[filtered_df["playerTeam"] == selected_team]

if selected_season != "All Seasons":
    filtered_df = filtered_df[filtered_df["season"] == int(selected_season)]


# Page title context
title_suffix = (
    selected_team if selected_team != "All Teams" else "League"
)
if selected_season != "All Seasons":
    title_suffix += f" — {selected_season}"


# ---------------------- Chart 1: Expected Goals % vs Rest ----------------------
st.subheader("📈 Expected Goals % by Rest Days")

xg_group = filtered_df.groupby("rest_bin")["xG%"].mean().reset_index()

if xg_group.empty:
    st.warning("Not enough data to compute xG% trends for this selection.")
else:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(xg_group["rest_bin"], xg_group["xG%"], marker="o", linewidth=2)

    ax.set_title(f"xG% vs Rest Days — {title_suffix}")
    ax.set_xlabel("Days of Rest")
    ax.set_ylabel("Average xG%")
    ax.grid(alpha=0.3)

    # Baseline line
    avg = filtered_df["xG%"].mean()
    ax.axhline(avg, linestyle="--", color="red", alpha=0.6)
    ax.text(0.1, avg + 0.3, f"Avg: {avg:.1f}%", color="red")

    st.pyplot(fig)


# ---------------------- Chart 2: Win Rate vs Rest ----------------------
st.subheader("🏆 Win Rate by Rest Days")

win_group = filtered_df.groupby("rest_bin")["win"].mean().reset_index()

if win_group.empty:
    st.warning("Not enough data to calculate win rate.")
else:
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.bar(win_group["rest_bin"], win_group["win"], color="#2ca02c")
    ax2.set_title(f"Win % by Rest — {title_suffix}")
    ax2.set_xlabel("Days of Rest")
    ax2.set_ylabel("Win %")
    ax2.grid(axis="y", alpha=0.3)
    st.pyplot(fig2)


# ---------------------- Summary Narration ----------------------
if not xg_group.empty and xg_group["xG%"].nunique() > 1:
    best_rest = xg_group.iloc[xg_group["xG%"].idxmax()]["rest_bin"]
    worst_rest = xg_group.iloc[xg_group["xG%"].idxmin()]["rest_bin"]

    st.success(
        f"Teams perform best after **{best_rest} days of rest**, "
        f"and struggle most after **{worst_rest} days**."
    )


# ---------------------- League-Wide Sensitivity Table ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking (League-Wide)")

league_sensitivity = rank_rest_sensitivity(df)

if league_sensitivity.empty:
    st.warning("Not enough sample size across the league to compute rankings.")
else:
    st.dataframe(league_sensitivity.style.format({"fatigue_score": "{:.2f}"}))


st.caption("📊 Data sourced from MoneyPuck — powered by nhlRestEffects.")
