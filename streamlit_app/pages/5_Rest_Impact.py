import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")


@st.cache_data
def load_data():
    """Load CSV using package, then fix formatting + compute rest."""

    df = load_rest_data("data/all_teams.csv").copy()

    # ------------------------------------------------------
    # 🚨 FIX: Correct broken date parsing from package
    # ------------------------------------------------------
    df["gameDate"] = (
        df["gameDate"]
        .astype(str)
        .str.extract(r"(\d{8})")[0]
        .apply(lambda x: pd.to_datetime(x, format="%Y%m%d", errors="coerce"))
    )

    # Team cleanup (handles TB/TBL, LAK/LA)
    df["playerTeam"] = df["playerTeam"].astype(str).str.strip().str.upper()
    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)

    # Use correct xG percentage column
    possible_xg_cols = ["xG%", "xGoalsPercentage", "xg_pct"]
    xg_col = next((c for c in possible_xg_cols if c in df.columns), None)

    df["xG"] = pd.to_numeric(df[xg_col], errors="coerce")

    # ------------------------------------------------------
    # Recalculate rest now that dates are correct
    # ------------------------------------------------------
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    def assign_rest(days):
        if pd.isna(days): 
            return None
        if days <= 1: return "0"   # Back-to-back or 1 day = no rest
        if days == 2: return "1"
        if days == 3: return "2"
        return "3+"

    df["rest_bucket"] = df["days_rest"].apply(assign_rest)

    # Remove first game & invalid cases
    df = df.dropna(subset=["rest_bucket", "xG"])

    return df


# ---- Load cleaned data ----
df = load_data()


# ---------------------- Sidebar Filters ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)


# ---------------------- Filter Data by UI ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]


# ---------------------- Debug Count Display ----------------------
st.caption(f"Rest bucket counts for {selected_team}")
st.write(team_df["rest_bucket"].value_counts().sort_index())


# ---------------------- Chart: xG by Rest ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("⚠️ Not enough data for this selection.")
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
        ax.text(x, y + 0.01, f"{y:.2f}", ha="center", fontsize=10)

    ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.5)
    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    st.pyplot(fig)


# ---------------------- League Ranking ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking (League-wide)")

league_df = df.copy()

if league_df.empty:
    st.warning("No league-wide data available.")
else:
    league_summary = (
        league_df.groupby(["playerTeam", "rest_bucket"])["xG"]
        .mean()
        .unstack()
        .reindex(columns=rest_order)
        .fillna(0)
    )

    league_summary["Fatigue Impact (0 → 3+)"] = league_summary["3+"] - league_summary["0"]
    league_summary = league_summary.sort_values("Fatigue Impact (0 → 3+)")

    st.dataframe(league_summary.style.format("{:.3f}"))


st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
