import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data


st.title("⏱️ Rest Impact Analysis")


# ---------------------- Load + Cache Data ----------------------
@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Fix dates robustly
    if pd.api.types.is_numeric_dtype(df["gameDate"]):
        df["gameDate"] = pd.to_datetime(df["gameDate"], unit="s", errors="coerce")
    else:
        df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")

    # Normalize team names (fix LA vs LAK, TB vs TBL)
    team_map = {
        "LA": "LAK", "L.A.": "LAK", "LOS": "LAK", "LA KINGS": "LAK",
        "TB": "TBL", "T.B.": "TBL", "TAM": "TBL"
    }
    df["playerTeam"] = df["playerTeam"].astype(str).str.upper().replace(team_map)

    # Detect xG% column
    possible_xg_cols = [
        "xG%", "xGoalsPercentage", "xGoalsPercent", "xg_pct",
        "expectedGoalsPct", "xGoals_Percent"
    ]
    
    xg_col = next((c for c in possible_xg_cols if c in df.columns), None)
    if xg_col is None:
        st.error("❌ No xG% column found — cannot compute rest analysis.")
        return df
    
    df["xG"] = pd.to_numeric(df[xg_col], errors="coerce")

    # Compute rest days
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Create rest bins
    def assign_rest(days):
        if pd.isna(days) or days < 0:
            return "0"
        if days == 0:
            return "0"
        elif days == 1:
            return "1"
        elif days == 2:
            return "2"
        else:
            return "3+"

    df["rest_bucket"] = df["days_rest"].apply(assign_rest)

    # Ensure win is numeric
    if "win" in df.columns:
        df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    return df


df = cached_rest_data()


# ---------------------- Sidebar Filters ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)


# ---------------------- Filter Data ----------------------
filtered = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    filtered = filtered[filtered["season"].astype(str) == selected_season]


# ---------------------- Plot Expected Goals by Rest ----------------------
st.subheader(f"📉 Expected Goals by Rest Days — {selected_team}")

summary = (
    filtered.groupby("rest_bucket")["xG"]
    .mean()
    .reset_index()
    .rename(columns={"xG": "Avg_xG"})
)

# Force all bins to appear
rest_order = ["0", "1", "2", "3+"]
summary = summary.set_index("rest_bucket").reindex(rest_order).fillna(0).reset_index()

if summary["Avg_xG"].sum() == 0:
    st.warning("Not enough xG data available to plot rest effects.")
else:
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(summary["rest_bucket"], summary["Avg_xG"], color="#1f77b4")
    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team}: xG% Compared Across Rest Days")
    ax.axhline(summary["Avg_xG"].mean(), linestyle="--", color="red", alpha=0.5)
    st.pyplot(fig)


# ---------------------- Fatigue Ranking Table ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

# Ranking logic: difference between "0 rest" and "3+ rest"
ranking = (
    df.groupby(["playerTeam", "rest_bucket"])["xG"]
    .mean()
    .reset_index()
    .pivot(index="playerTeam", columns="rest_bucket", values="xG")
)

ranking = ranking.reindex(columns=rest_order).fillna(0)
ranking["Fatigue Impact (0 → 3+)"] = ranking["3+"] - ranking["0"]

ranking = ranking.sort_values("Fatigue Impact (0 → 3+)")
st.dataframe(ranking.style.format("{:.3f}"))


st.caption("Data sourced from MoneyPuck.com — Analysis powered by nhlRestEffects.")
