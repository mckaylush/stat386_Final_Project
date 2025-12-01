import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev
from nhlRestEffects.analysis import rank_rest_sensitivity

st.title("⏱️ Rest Impact Analysis")

# ---------------------- Load & Cache ----------------------
@st.cache_data
def get_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Normalize team names
    df["playerTeam"] = df["playerTeam"].astype(str).str.strip().str.upper()
    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)

    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")
    df = df.sort_values(["playerTeam", "gameDate"])

    # Calculate rest days
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Bin rest days like original project
    df["rest_bin"] = df["days_rest"].apply(
        lambda x: "5+" if pd.notna(x) and x >= 5 else ("0" if x == 0 else (str(int(x)) if pd.notna(x) else np.nan))
    )

    # Ensure key columns are numeric
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)
    df["xGoalsPercentage"] = pd.to_numeric(df["xGoalsPercentage"], errors="coerce")

    return df.dropna(subset=["rest_bin"])


df = get_rest_data()

# ---------------------- Sidebar Filters ----------------------
st.sidebar.header("Filters")

teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].unique())

selected_team = st.sidebar.selectbox("Team", ["All Teams"] + teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + [str(s) for s in seasons])


# Apply filters
filtered_df = df.copy()

if selected_team != "All Teams":
    filtered_df = filtered_df[filtered_df["playerTeam"] == selected_team]

if selected_season != "All Seasons":
    filtered_df = filtered_df[filtered_df["season"] == int(selected_season)]


# ---------------------- xG% Chart ----------------------
st.subheader("📈 Expected Goals % by Rest Days")

xg_summary = filtered_df.groupby("rest_bin")["xGoalsPercentage"].mean().reset_index()

if xg_summary.empty:
    st.warning("Not enough data to calculate xG% trends for this selection.")
else:
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(xg_summary["rest_bin"], xg_summary["xGoalsPercentage"], marker="o", linewidth=2)
    ax1.set_ylabel("Avg xG%")
    ax1.set_xlabel("Days of Rest")
    ax1.set_title(f"xG% vs Rest Days — {selected_team if selected_team!='All Teams' else 'League'}")
    ax1.grid(alpha=0.3)

    league_avg = filtered_df["xGoalsPercentage"].mean()
    ax1.axhline(league_avg, linestyle="--", color="red", alpha=0.7)
    ax1.text(0.5, league_avg + 0.3, f"Avg: {league_avg:.1f}%", color="red")

    st.pyplot(fig1)


# ---------------------- Win % Chart ----------------------
st.subheader("🏆 Win Rate by Rest Days")

win_summary = filtered_df.groupby("rest_bin")["win"].mean().reset_index()

if win_summary.empty:
    st.warning("Not enough data to display win rate trends.")
else:
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.bar(win_summary["rest_bin"], win_summary["win"], color="#2ca02c")
    ax2.set_ylabel("Win %")
    ax2.set_xlabel("Days of Rest")
    ax2.set_title(f"Win Percentage by Rest — {selected_team if selected_team!='All Teams' else 'League'}")
    ax2.grid(axis="y", alpha=0.3)

    st.pyplot(fig2)


# ---------------------- Takeaway ----------------------
if not xg_summary.empty and xg_summary["xGoalsPercentage"].nunique() > 1:
    best = xg_summary.iloc[xg_summary["xGoalsPercentage"].idxmax()]["rest_bin"]
    worst = xg_summary.iloc[xg_summary["xGoalsPercentage"].idxmin()]["rest_bin"]

    st.success(
        f"Teams perform best after **{best} days of rest**, and tend to struggle most after **{worst} days**."
    )


# ---------------------- Fatigue Sensitivity Table ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

sensitivity = rank_rest_sensitivity(filtered_df)

if sensitivity.empty:
    st.warning("Not enough sample size to compute fatigue scores.")
else:
    st.dataframe(sensitivity.style.format({"fatigue_score": "{:.2f}"}))


st.caption("📊 Data sourced from MoneyPuck — processed using nhlRestEffects.")
