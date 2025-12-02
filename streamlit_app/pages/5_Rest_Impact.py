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

# ---------------------- Metrics for Comparison ----------------------
metrics = {
    "xG%": "xG",              # Expected goals % from your dataset
    "xGF": "xGoalsFor",       # Expected goals for
    "xGA": "xGoalsAgainst",   # Expected goals against
    "GF": "goalsFor",         # Actual goals for
    "GA": "goalsAgainst",     # Actual goals against
}


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

# ---------------------- League + Team Comparison Chart ----------------------
st.subheader("📊 Team vs League — Metric Breakdown by Rest Days")

# Build league average dataset
league_avg = (
    df.groupby("rest_bucket")[list(metrics.values())]
    .mean()
    .reset_index()
)
league_avg["Group"] = "League Avg"

# Build team-specific dataset
team_values = (
    team_df.groupby("rest_bucket")[list(metrics.values())]
    .mean()
    .reset_index()
)
team_values["Group"] = selected_team

# Combine
plot_df = pd.concat([team_values, league_avg], ignore_index=True)

# Rename rest bucket and metric names
plot_df["rest_bucket"] = plot_df["rest_bucket"].astype(str)
plot_df.rename(columns=metrics, inplace=True)

# Melt long format for plotting
long_df = plot_df.melt(
    id_vars=["rest_bucket", "Group"],
    var_name="Metric",
    value_name="Value"
)

# Ensure ordering
long_df["rest_bucket"] = pd.Categorical(long_df["rest_bucket"], categories=rest_order, ordered=True)

if long_df.empty:
    st.warning("⚠️ Not enough data to build comparison chart.")
else:
    # Pivot for chart layout: Metric → Row grouping
    pivot = long_df.pivot_table(
        index=["Metric", "Group"],
        columns="rest_bucket",
        values="Value",
        aggfunc="mean"
    ).reindex(columns=rest_order)

    st.write("📋 Comparison Table", pivot.style.format("{:.2f}"))

    # ---------------------- Heatmap-like chart ----------------------
    fig, ax = plt.subplots(figsize=(11, 6))

    im = ax.imshow(pivot, cmap="coolwarm")

    ax.set_xticks(range(len(rest_order)))
    ax.set_xticklabels(rest_order)

    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{idx[0]} — {idx[1]}" for idx in pivot.index])

    plt.colorbar(im, ax=ax)
    ax.set_title(f"{selected_team} vs League — Metric Strength by Rest Days")

    st.pyplot(fig)


st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
