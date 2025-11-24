import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from nhlRestEffects.data_loader import load_rest_data, enrich_with_rest_metrics
from nhlRestEffects.analysis import (
    add_rolling_metrics,
    summarize_rest_buckets,
    rank_rest_sensitivity,
    assign_rest_bucket,
    compute_days_rest
)

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Ensure proper datetime formatting
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")

    # ---- Compute days rest CORRECTLY ----
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    print("DEBUG days_rest:", df["days_rest"].head(50).tolist())  # TEMP DEBUG

    # ---- Compute rest bucket ----
    df["rest_bucket"] = df["days_rest"].apply(assign_rest_bucket)

    # ---- Convert win column to numeric ----
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    # ---- Ensure xG% is numeric ----
    df["xG%"] = pd.to_numeric(df["xG%"], errors="coerce")

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
