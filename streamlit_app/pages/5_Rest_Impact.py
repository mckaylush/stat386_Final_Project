import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from nhlRestEffects.data_loader import load_rest_data


st.title("⏱️ Rest Impact Analysis")


# ---------------------- Helper: Fix Dates ----------------------
def fix_dates(df):
    """Robust conversion of gameDate → datetime."""
    
    # Already datetime? Return
    if pd.api.types.is_datetime64_any_dtype(df["gameDate"]):
        return df

    # If numeric → likely UNIX milliseconds (MoneyPuck format)
    if pd.api.types.is_numeric_dtype(df["gameDate"]):
        parsed = pd.to_datetime(df["gameDate"], unit="ms", errors="coerce")

        # If still showing mostly 1970 → fallback to seconds
        if parsed.dt.year.mode()[0] == 1970:
            parsed = pd.to_datetime(df["gameDate"], unit="s", errors="coerce")

        df["gameDate"] = parsed
        return df

    # Otherwise treat as string date
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")
    return df


# ---------------------- Load + Cache Data ----------------------
@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # Fix bad dates
    df = fix_dates(df)

    # Normalize team names (fix LA vs LAK, TB vs TBL)
    team_map = {
        "LA": "LAK", "L.A.": "LAK", "LOS": "LAK", "LA KINGS": "LAK",
        "TB": "TBL", "T.B.": "TBL", "TAM": "TBL"
    }
    df["playerTeam"] = df["playerTeam"].astype(str).str.upper().replace(team_map)

    # Detect xG% column
    possible_cols = ["xG%", "xGoalsPercentage", "xg_pct", "xGoalsPercent"]
    xg_col = next((c for c in possible_cols if c in df.columns), None)

    if xg_col is None:
        st.error("❌ No expected goals % column found.")
        return df

    df["xG"] = pd.to_numeric(df[xg_col], errors="coerce")

    # Ensure win column usable
    if "win" in df.columns:
        df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    # Calculate rest days
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Assign bins → 0,1,2,3+
    def assign_rest(days):
        if pd.isna(days) or days < 0:
            return "0"
        elif days == 0:
            return "0"
        elif days == 1:
            return "1"
        elif days == 2:
            return "2"
        else:
            return "3+"

    df["rest_bucket"] = df["days_rest"].apply(assign_rest)

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


# ---------------------- Expected Goals Plot ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

summary = (
    filtered.groupby("rest_bucket")["xG"]
    .mean()
    .reset_index()
    .rename(columns={"xG": "Avg_xG"})
)

# Ensure all bins appear even if empty
rest_order = ["0", "1", "2", "3+"]
summary = summary.set_index("rest_bucket").reindex(rest_order).fillna(0).reset_index()

if summary["Avg_xG"].sum() == 0:
    st.warning("Not enough data to display expected goals impact.")
else:
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(summary["rest_bucket"], summary["Avg_xG"], color="#1f77b4")
    ax.set_ylabel("Average Expected Goals %")
    ax.set_xlabel("Rest Category (Days)")
    ax.set_title(f"{selected_team}: xG% Compared by Rest Category")
    ax.axhline(summary["Avg_xG"].mean(), linestyle="--", color="red", alpha=0.4)
    st.pyplot(fig)


# ---------------------- Fatigue Sensitivity Ranking ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

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
