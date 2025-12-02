import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.utils import clean_team_abbrev  # still use helper

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def load_data():
    # --- Load raw CSV directly (NOT the loader) ---
    df = pd.read_csv("./data/all_teams.csv").copy()

    # --- Fix gameDate format (YYYYMMDD) ---
    df["gameDate"] = (
        df["gameDate"]
        .astype(str)
        .str.extract(r"(\d{8})")[0]
    )

    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d", errors="coerce")

    # --- Clean team abbreviations ---
    df["playerTeam"] = (
        df["playerTeam"]
        .astype(str)
        .str.upper()
        .str.strip()
        .apply(clean_team_abbrev)
    )
    
    # 🔧 Final hard override to merge stray abbreviations:
    team_fix = {
        "LA": "LAK", "L.A.": "LAK", "LOS": "LAK", "LA KINGS": "LAK",
        "TB": "TBL", "T.B.": "TBL", "TAM": "TBL", "TAMPA BAY": "TBL"
    }
    df["playerTeam"] = df["playerTeam"].replace(team_fix)

    # --- Use correct xG% metric ---
    if "xG%" in df.columns:
        df["xG"] = pd.to_numeric(df["xG%"], errors="coerce")
    else:
        df["xG"] = pd.to_numeric(df["xGoalsPercentage"], errors="coerce")

    # --- Sort and compute rest days ---
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # --- Bucket rest days into NHL logic ---
    def bucket(days):
        if pd.isna(days):
            return "0"  # first game treated as neutral
        if days <= 1:
            return "0"  # back-to-back = 0 days rest
        if days == 2:
            return "1"
        if days == 3:
            return "2"
        return "3+"

    df["rest_bucket"] = df["days_rest"].apply(bucket)

    # --- Return cleaned dataset ---
    return df.dropna(subset=["xG"])


df = load_data()

# ---------------------- Sidebar ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

# ---------------------- Filter ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

team_df = team_df.dropna(subset=["xG", "rest_bucket"])

# ---------------------- Chart ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("⚠️ Not enough data.")
else:
    summary = (
        team_df.groupby("rest_bucket")["xG"]
        .mean()
        .reindex(rest_order)
        .fillna(0)
    )

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(rest_order, summary.values, edgecolor="black")

    for x, val in zip(rest_order, summary.values):
        ax.text(x, val -.1, f"{val:.2f}", ha="center")

    ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.5)
    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    st.pyplot(fig)

# ---------------------- League Comparison (Improved) ----------------------
st.subheader("📋 Rest Performance Comparison")

metrics = {
    "xG%": "xG",
    "xGF": "xGoalsFor",
    "xGA": "xGoalsAgainst",
    "GF": "goalsFor",
    "GA": "goalsAgainst",
}

# Compute selected team stats by rest bucket
team_stats = (
    team_df.groupby("rest_bucket")[list(metrics.values())]
    .mean()
    .reindex(rest_order)
)

# Compute league averages for comparison
league_stats = (
    df.groupby("rest_bucket")[list(metrics.values())]
    .mean()
    .reindex(rest_order)
)

# Rename rows for clarity
team_stats.index = [f"{selected_team} ({r})" for r in rest_order]
league_stats.index = [f"League Avg ({r})" for r in rest_order]

comparison_df = pd.concat([team_stats, league_stats])

# Rename columns to clean labels
comparison_df = comparison_df.rename(columns={v: k for k, v in metrics.items()})

# Display table
st.dataframe(comparison_df.style.format("{:.2f}"))


st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
