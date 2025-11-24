import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyploy as plt
from nhlRestEffects.data_loader import load_rest_data, enrich_with_rest_metrics
from nhlRestEffects.analysis import (
    add_rolling_metrics,
    summarize_rest_buckets,
    rank_rest_sensitivity,
    assign_rest_bucket
)

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Ensure proper numeric conversion
    numeric_cols = ["xGoalsPercentage", "goalsFor", "goalsAgainst", "xGoalsAgainst", "xOnGoalFor"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Ensure xG% exists
    if "xG%" not in df.columns:
        df["xG%"] = df["xGoalsPercentage"]

    # Create goal diff
    if "goal_diff" not in df.columns:
        df["goal_diff"] = df["goalsFor"] - df["goalsAgainst"]

    # Create win column
    if "win" not in df.columns:
        df["win"] = (df["goalsFor"] > df["goalsAgainst"]).astype(int)

    # Create rest_days if missing
    if "rest_days" not in df.columns:
        df["rest_days"] = np.nan  # fallback

    # Create rest bucket
    df["rest_bucket"] = df["rest_bucket"].fillna(
        df["rest_days"].apply(assign_rest_bucket)
    )

    return df


df = cached_rest_data()

# Debug panel (you can remove later)
with st.expander("🛠 Debug Info"):
    st.write(df.head())
    st.write(df.columns.tolist())

# ============================
# 📊 Rest vs xG% Plot
# ============================
st.subheader("📈 Rest vs Expected Goals Performance")

summary = summarize_rest_buckets(df)

if summary.empty:
    st.warning("Not enough data to compare rest buckets.")
else:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(summary["rest_bucket"], summary["xg_pct"])
    ax.set_ylabel("Avg xG%")
    ax.set_title("Expected Goals Percentage by Rest Days")
    st.pyplot(fig)

# ============================
# 🧠 Team Sensitivity Table
# ============================
st.subheader("🏒 Teams Most Affected by Fatigue")

fatigue_rank = rank_rest_sensitivity(df)

if fatigue_rank.empty:
    st.warning("Not enough data to calculate rest sensitivity.")
else:
    st.dataframe(fatigue_rank.style.format("{:.2f}"))

st.caption("Data powered by MoneyPuck & `nhlRestEffects` package.")
