import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import rank_rest_sensitivity

st.title("⏱️ Rest Impact on Team Performance")

@st.cache_data
def get_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Fix and sort
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Cap rest days like original design
    df["rest_bin"] = df["days_rest"].apply(lambda x: "5+" if x >= 5 else int(x) if not pd.isna(x) else np.nan)

    # Clean numeric columns
    df["xGoalsPercentage"] = pd.to_numeric(df["xGoalsPercentage"], errors="coerce")
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    return df.dropna(subset=["rest_bin"])

df = get_rest_data()

# ============================
# 📈 xG% vs Rest Days
# ============================
st.subheader("📊 Expected Goals % by Rest Days")

xg_summary = df.groupby("rest_bin")["xGoalsPercentage"].mean().reset_index()

if xg_summary.empty:
    st.warning("Not enough data to display xG% trends.")
else:
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(xg_summary["rest_bin"], xg_summary["xGoalsPercentage"], marker="o", linewidth=2)
    ax1.set_ylabel("Average xG%")
    ax1.set_xlabel("Days of Rest")
    ax1.set_title("xG% Change Based on Rest Days")
    ax1.grid(alpha=0.3)

    # league mean line
    league_avg = df["xGoalsPercentage"].mean()
    ax1.axhline(league_avg, linestyle="--", color="red", alpha=0.7)
    ax1.text(0.5, league_avg + 0.3, f"League Avg ({league_avg:.1f}%)", color="red")

    st.pyplot(fig1)

# ============================
# 📈 Win % vs Rest Days
# ============================
st.subheader("🏆 Win Rate by Rest Days")

win_summary = df.groupby("rest_bin")["win"].mean().reset_index()

if win_summary.empty:
    st.warning("Not enough data to display win trends.")
else:
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.bar(win_summary["rest_bin"], win_summary["win"], color="#2ca02c")
    ax2.set_ylabel("Win Percentage")
    ax2.set_xlabel("Days of Rest")
    ax2.set_title("Win Rate Change Based on Rest")
    ax2.grid(axis="y", alpha=0.3)

    st.pyplot(fig2)

# ============================
# 🧠 Summary Takeaway
# ============================
if not xg_summary.empty and not win_summary.empty:
    best = xg_summary.iloc[xg_summary["xGoalsPercentage"].idxmax()]["rest_bin"]
    worst = xg_summary.iloc[xg_summary["xGoalsPercentage"].idxmin()]["rest_bin"]
    st.success(
        f"Teams perform **best after {best} days of rest**, and struggle most after **{worst} days**."
    )


# ============================
# 🏒 Fatigue Sensitivity Ranking
# ============================
st.subheader("📋 Which Teams Are Most Fatigue-Sensitive?")

ranking = rank_rest_sensitivity(df)

if ranking.empty:
    st.warning("Not enough data to rank fatigue sensitivity.")
else:
    st.dataframe(
        ranking.style.format({"fatigue_score": "{:.2f}"}).highlight_max("fatigue_score")
    )

st.caption("📊 Data sourced from MoneyPuck.com — processed using nhlRestEffects.")
