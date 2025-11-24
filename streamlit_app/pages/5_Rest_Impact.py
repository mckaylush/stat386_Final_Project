import streamlit as st
import numpy as np
import pandas as pd
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
    df = load_rest_data("data/all_teams.csv")

    # ---- Normalize column names ----
    rename_map = {
        "xGoalsPercentage": "xG%",
        "goalsFor": "goalsFor",
        "goalsAgainst": "goalsAgainst",
        "gameDate": "game_date"
    }
    df = df.rename(columns=rename_map)

    # ---- Convert numerics safely ----
    numeric_cols = ["xG%", "goalsFor", "goalsAgainst"]

    for col in numeric_cols:
        if col in df.columns and isinstance(df[col], pd.Series):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---- Derived fields ----
    df["goal_diff"] = df["goalsFor"] - df["goalsAgainst"]

    # If missing, create placeholders for rest/day metrics
    if "days_rest" not in df.columns:
        df["days_rest"] = np.nan

    df["rest_bucket"] = df["days_rest"].apply(assign_rest_bucket)

    return df

df = cached_rest_data()

# ---------------------- FILTERS ----------------------
teams = sorted(df["team"].unique())
seasons = sorted(df["season"].unique())

selected_team = st.sidebar.selectbox("Team:", teams)
selected_season = st.sidebar.selectbox("Season:", ["All"] + seasons)

filtered = df[df["team"] == selected_team].copy()
if selected_season != "All":
    filtered = filtered[filtered["season"] == selected_season]

# ---------------------- VIEW ----------------------
st.subheader(f"📈 Rest vs Expected Goals Performance")

fig, ax = plt.subplots(figsize=(10, 5))
ax.scatter(filtered["daysRest"], filtered["xGoalsPercentage"], alpha=0.7)
ax.set_xlabel("Days of Rest")
ax.set_ylabel("Expected Goals % (xG%)")
ax.grid(alpha=0.2)

st.pyplot(fig)

# Summary Stats
avg = filtered.groupby("daysRest")["xGoalsPercentage"].mean().reset_index()
st.subheader("📋 Average xG% by Rest Days")
st.table(avg.style.format("{:.2f}"))

st.caption("Powered by nhlRestEffects package")
