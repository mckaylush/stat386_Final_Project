import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")


@st.cache_data
def load_data():
    df = load_rest_data("data/all_teams.csv").copy()

    st.write("📌 RAW COLUMNS FROM PACKAGE:", df.columns.tolist())
    st.dataframe(df.head())


    # ------------------ FIX DATE PARSING ------------------
    df["gameDate"] = (
        df["gameDate"]
        .astype(str)
        .str.extract(r"(\d{8})")[0]   # keep YYYYMMDD pattern
        .apply(lambda x: pd.to_datetime(x, format="%Y%m%d", errors="coerce"))
    )

    # ------------------ CLEAN TEAM LABELS ------------------
    df["playerTeam"] = df["playerTeam"].astype(str).str.upper().apply(clean_team_abbrev)

    # ------------------ FIND CORRECT xG COLUMN ------------------
    xg_candidates = ["xGoalsPercentage", "xG%", "xg_pct", "xGoalsPercent"]
    xg_col = next((c for c in xg_candidates if c in df.columns), None)

    if not xg_col:
        st.error("❌ No xG% column found in dataset.")
        return pd.DataFrame()

    df["xG"] = pd.to_numeric(df[xg_col], errors="coerce")

    # ------------------ COMPUTE REST DAYS ------------------
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    def assign_rest(days):
        if pd.isna(days): return None
        if days <= 1: return "0"   # back-to-back or 1 day gap
        if days == 2: return "1"
        if days == 3: return "2"
        return "3+"

    df["rest_bucket"] = df["days_rest"].apply(assign_rest)

    # ------------------ DROP INVALID ROWS ------------------
    df = df.dropna(subset=["rest_bucket", "xG"])

    return df


# ------------------ LOAD CLEAN DATA ------------------
df = load_data()

st.write("DEBUG:", df.head())  # TEMP to verify it isn't empty


# ------------------ SIDEBAR ------------------
if df.empty:
    st.error("❌ Data empty after preparation — check column names and filtering.")
    st.stop()

teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)


# ------------------ FILTER ------------------
team_df = df[df["playerTeam"] == selected_team].copy()
if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]


# ------------------ REST BUCKET COUNT ------------------
st.caption(f"Rest bucket counts for {selected_team}")
st.write(team_df["rest_bucket"].value_counts().sort_index())


# ------------------ MAIN CHART ------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("⚠️ Not enough data to plot for this selection.")
else:
    summary = (
        team_df.groupby("rest_bucket")["xG"]
        .mean()
        .reindex(rest_order)
        .fillna(0)
    )

    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(rest_order, summary.values, edgecolor="black")

    for x, y in zip(rest_order, summary.values):
        ax.text(x, y + 0.01, f"{y:.2f}", ha="center")

    ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.5)
    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    st.pyplot(fig)


# ------------------ LEAGUE RANKING ------------------
st.subheader("📋 Fatigue Sensitivity Ranking (League-wide)")

league = df.copy()

league_summary = (
    league.groupby(["playerTeam", "rest_bucket"])["xG"]
    .mean()
    .unstack()
    .reindex(columns=rest_order)
    .fillna(0)
)

league_summary["Fatigue Impact (0 → 3+)"] = league_summary["3+"] - league_summary["0"]
league_summary = league_summary.sort_values("Fatigue Impact (0 → 3+)")

st.dataframe(league_summary.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
