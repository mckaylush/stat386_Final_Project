import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def load_data():
    # Load already-processed MoneyPuck dataset through your package
    df = load_rest_data("data/all_teams.csv").copy()

    # Fix gameDate (it came in wrong format → convert YYYYMMDD properly)
    df["gameDate"] = (
        df["gameDate"]
        .astype(str)
        .str.extract(r"(\d{8})")[0]  # ensure only YYYYMMDD
    )
    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d", errors="coerce")

    # Standardize team naming
    df["playerTeam"] = df["playerTeam"].astype(str).apply(clean_team_abbrev)

    # Use package-computed expected goals %
    df["xG"] = pd.to_numeric(df["xG%"], errors="coerce")

    # Keep only valid rows
    return df.dropna(subset=["xG", "rest_bucket", "gameDate"])


df = load_data()

# ---------------------- Sidebar ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

# ---------------------- Filter Data ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()
if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

# ---------------------- Debug Counts ----------------------
st.caption(f"Rest bucket counts for {selected_team}")
st.write(team_df["rest_bucket"].value_counts().sort_index())

# ---------------------- Chart ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("⚠️ Not enough data for this selection.")
else:
    summary = team_df.groupby("rest_bucket")["xG"].mean().reindex(rest_order).fillna(0)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(rest_order, summary.values, edgecolor="black")

    for x, v in zip(rest_order, summary.values):
        ax.text(x, v + 0.01, f"{v:.2f}", ha="center")

    ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.5)
    ax.set_ylabel("Avg xG%")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    st.pyplot(fig)

# ---------------------- League Ranking ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

league_table = (
    df.groupby(["playerTeam", "rest_bucket"])["xG"]
    .mean()
    .unstack()
    .reindex(columns=rest_order)
    .fillna(0)
)

league_table["Fatigue Impact (0 → 3+)"] = league_table["3+"] - league_table["0"]
league_table = league_table.sort_values("Fatigue Impact (0 → 3+)")

st.dataframe(league_table.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
