import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import (
    summarize_rest_buckets,
    rank_rest_sensitivity,
    assign_rest_bucket
)


# ---------------------- PAGE TITLE ----------------------
st.title("⏱️ Rest Impact on Team Performance")


# ---------------------- DATA LOADING ----------------------
@st.cache_data
def load_clean_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Ensure proper datetime formatting
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")

    # Compute rest days
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Assign rest buckets (B version)
    def bucket(x):
        if pd.isna(x): return None
        if x == 0: return "0 Days (B2B)"
        if x == 1: return "1 Day"
        if x == 2: return "2 Days"
        return "3+ Days"

    df["rest_bucket"] = df["days_rest"].apply(bucket)

    # Clean numeric metrics
    df["xG%"] = pd.to_numeric(df["xG%"], errors="coerce")
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    return df


df = load_clean_rest_data()


# ---------------------- SIDEBAR FILTERS ----------------------
st.sidebar.header("Filters")

teams = ["League Average"] + sorted(df["playerTeam"].unique().tolist())
selected_team = st.sidebar.selectbox("Team", teams)

rolling_window = st.sidebar.selectbox("Rolling Window", [1, 5, 10], index=1)


# ---------------------- TEAM FILTER ----------------------
if selected_team == "League Average":
    filtered_df = df.copy()
else:
    filtered_df = df[df["playerTeam"] == selected_team].copy()


# ---------------------- LINE CHART (Team Only) ----------------------
if selected_team != "League Average":
    st.subheader(f"📈 {selected_team} — Rolling xG% Trend by Rest")

    filtered_df = filtered_df.sort_values("gameDate")
    filtered_df["xG_roll"] = filtered_df["xG%"].rolling(rolling_window).mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(filtered_df["gameDate"], filtered_df["xG_roll"], linewidth=2, color="#1f77b4")
    ax.set_ylabel("Rolling xG%")
    ax.set_xlabel("Date")
    ax.grid(alpha=0.3)

    # Show rest markers
    for idx, row in filtered_df.iterrows():
        if row["days_rest"] == 0:
            ax.scatter(row["gameDate"], row["xG_roll"], color="red", s=50, label="_nolegend_")

    st.pyplot(fig)


# ---------------------- BAR CHART — REST BUCKETS ----------------------
st.subheader("📊 Performance by Rest Category")

summary = summarize_rest_buckets(filtered_df)

if not summary.empty:
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.bar(summary["rest_bucket"], summary["xg_pct"], color="#1f77b4")
    ax2.set_ylabel("Avg xG%")
    ax2.set_xlabel("Rest Category")
    ax2.set_title("Expected Goals % by Rest Bucket")
    ax2.grid(axis="y", alpha=0.2)

    # Labels on bars
    for i, v in enumerate(summary["xg_pct"]):
        ax2.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=10)

    st.pyplot(fig2)

    # Insight sentence
    best = summary.sort_values("xg_pct", ascending=False).iloc[0]
    worst = summary.sort_values("xg_pct").iloc[0]

    st.success(
        f"💡 Teams perform best on **{best['rest_bucket']}** games and struggle most on **{worst['rest_bucket']}**."
    )


# ---------------------- FATIGUE RANKING TABLE ----------------------
st.subheader("🏒 Fatigue Sensitivity Rankings")

fatigue = rank_rest_sensitivity(df)

if not fatigue.empty:
    fatigue = fatigue.rename(columns={
        "fatigue_index": "Fatigue Impact Score",
        "xg_diff": "xG% Drop from Rest"
    })

    st.dataframe(fatigue.style.format({"Fatigue Impact Score": "{:.2f}", "xG% Drop from Rest": "{:.2f}"}))


# ---------------------- FOOTER ----------------------
st.caption("Data sourced from MoneyPuck.com — analyzed using `nhlRestEffects`.")
