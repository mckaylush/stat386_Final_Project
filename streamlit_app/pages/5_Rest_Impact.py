import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import summarize_rest_buckets, rank_rest_sensitivity


st.title("⏱️ Rest Impact Analysis")


# ---------------------- TEAM NAME CLEANING ----------------------
def clean_team_abbrev(team):
    """Normalize team abbreviations so TB=TBL and LA=LAK etc."""
    mapping = {
        "T.B.": "TBL", "TB": "TBL", "TAM": "TBL",
        "S.J.": "SJS", "SJ": "SJS", "SAN": "SJS",
        "N.J.": "NJD", "NJ": "NJD",
        "L.A.": "LAK", "LA": "LAK"
    }
    team = str(team).strip().upper()
    return mapping.get(team, team)


# ---------------------- DATE FIXING ----------------------
def fix_dates(df):
    """Attempts to recover the correct date column from MoneyPuck format."""
    possible_date_cols = ["gameDate", "date", "date_game", "game_date", "GameDate"]

    real_col = None
    for c in possible_date_cols:
        if c in df.columns:
            real_col = c
            break

    if real_col is None:
        raise ValueError("No usable date column found in dataset.")

    # Attempt datetime conversion
    df[real_col] = pd.to_datetime(df[real_col], errors="coerce")

    # If many dates were NaT and column is numeric → try unix timestamps
    if df[real_col].isna().sum() > 10 and pd.api.types.is_numeric_dtype(df[real_col]):
        df[real_col] = pd.to_datetime(df[real_col], unit="s", errors="coerce")

    df["gameDate"] = df[real_col]
    return df


# ---------------------- LOAD DATA ----------------------
@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    df = fix_dates(df)

    # Clean team names
    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)

    # Ensure sorting before rest calculation
    df = df.sort_values(["playerTeam", "gameDate"])

    # Calculate rest days
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Handle bad values
    df["days_rest"] = df["days_rest"].fillna(0).clip(lower=0, upper=10)

    # Assign rest bucket
    df["rest_bucket"] = df["days_rest"].apply(
        lambda x: "0 Days" if x == 0 else
                  "1 Day" if x == 1 else
                  "2 Days" if x == 2 else
                  "3+ Days"
    )

    # Ensure numeric xG%
    df["xG%"] = pd.to_numeric(df["xG%"], errors="coerce")

    return df


df = cached_rest_data()


# ---------------------- SIDEBAR FILTERS ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = ["All Seasons"] + sorted(df["season"].unique())

selected_team = st.sidebar.selectbox("Team", teams)
selected_season = st.sidebar.selectbox("Season", seasons)

filtered = df[df["playerTeam"] == selected_team]

if selected_season != "All Seasons":
    filtered = filtered[filtered["season"] == selected_season]


# ---------------------- SUMMARY PLOT ----------------------
st.subheader(f"📈 Expected Goals by Rest Days — {selected_team}")

summary = summarize_rest_buckets(filtered)

if summary.empty:
    st.warning("Not enough data for this selection.")
else:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(summary["rest_bucket"], summary["xg_pct"], color="#1f77b4")
    ax.set_ylabel("Average Expected Goals %")
    ax.set_title(f"{selected_team}: xG% Compared Across Rest Days")
    st.pyplot(fig)


# ---------------------- RANKING TABLE ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

ranking = rank_rest_sensitivity(df)

if ranking.empty:
    st.warning("Not enough sample size to compute fatigue scores.")
else:
    st.dataframe(ranking.style.format({"fatigue_score": "{:.2f}"}))


# ---------------------- FOOTER ----------------------
st.caption("Data sourced from MoneyPuck.com — Analysis powered by nhlRestEffects.")
