import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import (
    assign_rest_bucket,
    summarize_rest_buckets,
    rank_rest_sensitivity
)

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def load_clean_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # ---- Fix Dates ----
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")

    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # ---- Categorize rest into buckets ----
    df["rest_bucket"] = df["days_rest"].apply(assign_rest_bucket)

    # Ensure numeric types exist cleanly
    df["xGoalsPercentage"] = pd.to_numeric(df["xGoalsPercentage"], errors="coerce")
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    return df

df = load_clean_rest_data()

# ================================
# 📈 Expected Goals vs Rest
# ================================
st.subheader("📊 Average Expected Goals % by Rest Category")

rest_summary = summarize_rest_buckets(df)

if rest_summary.empty:
    st.warning("Not enough data available to calculate rest effects.")
else:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(rest_summary["rest_bucket"], rest_summary["xg_pct"], color="#1f77b4")
    ax.set_ylabel("Average xG%")
    ax.set_xlabel("Rest Days Category")
    ax.set_title("Performance Change Relative to Rest")
    ax.grid(alpha=0.3, axis="y")

    # Draw mean line
    overall_avg = df["xGoalsPercentage"].mean()
    ax.axhline(overall_avg, linestyle="--", color="red", alpha=0.7)
    ax.text(
        0.1, overall_avg + 0.5,
        f"League Average ({overall_avg:.1f}%)",
        color="red"
    )

    st.pyplot(fig)


# ================================
# 🧠 Summary Takeaway
# ================================
if not rest_summary.empty:
    best_bucket = rest_summary.iloc[rest_summary["xg_pct"].idxmax()]["rest_bucket"]
    worst_bucket = rest_summary.iloc[rest_summary["xg_pct"].idxmin()]["rest_bucket"]

    st.success(
        f"Teams tend to perform **best** after **{best_bucket}**, and struggle most after **{worst_bucket}**."
    )


# ================================
# 🏒 Fatigue Sensitivity Ranking
# ================================
st.subheader("🏒 Teams Most Affected by Fatigue")

ranking = rank_rest_sensitivity(df)

if ranking.empty:
    st.warning("Not enough data to produce a fatigue ranking.")
else:
    st.dataframe(
        ranking.style.format({"fatigue_score": "{:.2f}"}).highlight_max("fatigue_score")
    )

st.caption("Data sourced from MoneyPuck + nhlRestEffects")
