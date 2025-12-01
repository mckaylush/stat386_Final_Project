import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import (
    summarize_rest_buckets,
    rank_rest_sensitivity,
    assign_rest_bucket
)


# ---------------------- PAGE TITLE ----------------------
st.title("⏱️ Rest Impact on Performance")


# ---------------------- CACHE DATA ----------------------
@st.cache_data
def load_clean_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Clean dates
    if not pd.api.types.is_datetime64_any_dtype(df["gameDate"]):
        df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")

    df = df.sort_values(["playerTeam", "gameDate"])

    # Compute rest
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days
    df["rest_bucket"] = df["days_rest"].apply(assign_rest_bucket)

    # Ensure clean numeric fields
    df["xG%"] = pd.to_numeric(df["xG%"], errors="coerce")
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    return df


df = load_clean_rest_data()


# ---------------------- SIDEBAR FILTER ----------------------
st.sidebar.header("Filters")

teams = ["League Average"] + sorted(df["playerTeam"].unique().tolist())
selected_team = st.sidebar.selectbox("Filter by Team", teams)

if selected_team != "League Average":
    df_filtered = df[df["playerTeam"] == selected_team]
else:
    df_filtered = df.copy()


# ---------------------- REST → PERFORMANCE BAR CHART ----------------------
st.subheader("📈 How Rest Affects Expected Goals (xG%)")

summary = summarize_rest_buckets(df_filtered)

if summary.empty:
    st.warning("Not enough data to visualize rest impact.")
else:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(summary["rest_bucket"], summary["xg_pct"], color="#1f77b4")
    ax.axhline(summary["xg_pct"].mean(), color="gray", linestyle="--", alpha=0.6)
    ax.set_ylabel("Average xG%")
    ax.set_xlabel("Rest Category")
    title_team = selected_team if selected_team != "League Average" else "League"
    ax.set_title(f"{title_team} Performance by Rest Category")

    # Label values
    for i, v in enumerate(summary["xg_pct"]):
        ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=10)

    st.pyplot(fig)


# ---------------------- INSIGHT BOX ----------------------
if not summary.empty:
    best_bucket = summary.sort_values("xg_pct", ascending=False).iloc[0]
    worst_bucket = summary.sort_values("xg_pct", ascending=True).iloc[0]

    st.success(
        f"💡 **Insight:** The biggest jump in performance happens when playing with **{best_bucket['rest_bucket']}**, "
        f"while performance declines most on **{worst_bucket['rest_bucket']}** games."
    )


# ---------------------- FATIGUE RANKINGS ----------------------
st.subheader("🏒 Which Teams Struggle Most on Low Rest?")

fatigue = rank_rest_sensitivity(df)

if fatigue.empty:
    st.warning("Not enough data to calculate fatigue effect across teams.")
else:
    st.dataframe(
        fatigue.style.format({
            "fatigue_index": "{:.2f}",
            "xg_diff": "{:.2f}"
        })
    )


# ---------------------- CAPTION ----------------------
st.caption("Data sourced from MoneyPuck.com — analyzed with `nhlRestEffects`.")
