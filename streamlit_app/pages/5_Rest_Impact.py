import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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

    # 🔧 Fix expected column names
    df.rename(columns={"rest_days": "days_rest"}, inplace=True)

    numeric_cols = ["xG%", "goal_diff", "days_rest"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["rest_bucket"] = df["days_rest"].apply(assign_rest_bucket)
    return df


df = cached_rest_data()

st.write("🔎 RAW HEAD")
st.write(df.head())

st.write("🔎 UNIQUE rest_bucket VALUES:", df["rest_bucket"].unique().tolist())
st.write("🔎 WIN VALUE COUNTS:", df["win"].value_counts(dropna=False).to_dict())

st.write("🔎 xG% TYPE:", df["xG%"].dtype)

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
