import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev  # if used elsewhere


st.title("⏱️ Rest Impact Analysis")


# ---------------------- Cached Data Loader ----------------------
@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    # ---- FIX DATE FORMAT (your dataset uses string YYYY-MM-DD format) ----
    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y-%m-%d", errors="coerce")

    # ---- Normalize Team Names (fix LA vs LAK, TB vs TBL) ----
    team_map = {
        "LA": "LAK", "L.A.": "LAK", "LOS": "LAK", "LOS ANGELES": "LAK",
        "TB": "TBL", "T.B.": "TBL", "TAM": "TBL", "TAMPA": "TBL"
    }
    df["playerTeam"] = df["playerTeam"].astype(str).str.upper().replace(team_map)

    # ---- Detect the correct xG% column ----
    possible_xg_cols = [
        "xGoalsPercentage", "xG%", "xGoalsPercent", "xg_pct", "expectedGoalsPct"
    ]
    xg_col = next((c for c in possible_xg_cols if c in df.columns), None)

    if xg_col is None:
        st.error("❌ No usable Expected Goals % column found.")
        return df

    df["xG"] = pd.to_numeric(df[xg_col], errors="coerce")

    # ---- Compute Days of Rest ----
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # ---- Assign Rest Buckets ----
    def assign_rest(days):
        if pd.isna(days) or days <= 0:
            return "0"
        elif days == 1:
            return "1"
        elif days == 2:
            return "2"
        else:
            return "3+"

    df["rest_bucket"] = df["days_rest"].apply(assign_rest)

    # ---- Ensure win column exists as int ----
    if "win" in df.columns:
        df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    return df


df = cached_rest_data()


# ---------------------- Sidebar Controls ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)


# ---------------------- Filter Selection ----------------------
filtered = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    filtered = filtered[filtered["season"].astype(str) == selected_season]


# ---------------------- Section: Expected Goals by Rest Bucket ----------------------
st.subheader(f"📈 Expected Goals % vs Rest — {selected_team}")

summary = (
    filtered.groupby("rest_bucket")["xG"]
    .mean()
    .reset_index()
    .rename(columns={"xG": "Avg_xG"})
)

# Force appearance of all bins even if empty
rest_order = ["0", "1", "2", "3+"]
summary = summary.set_index("rest_bucket").reindex(rest_order).fillna(0).reset_index()

if summary["Avg_xG"].sum() == 0:
    st.warning("⚠️ Not enough xG data to plot for this selection.")
else:
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(summary["rest_bucket"], summary["Avg_xG"], color="#1f77b4", edgecolor="black")

    # Label bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 0.01,
                f"{height:.2f}", ha="center", fontsize=10)

    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Expected Goals % by Rest Level")
    ax.axhline(summary["Avg_xG"].mean(), linestyle="--", color="red", alpha=0.5)

    st.pyplot(fig)


# ---------------------- Section: Fatigue Sensitivity Ranking ----------------------
st.subheader("🏒 League Comparison: Fatigue Sensitivity")

ranking = (
    df.groupby(["playerTeam", "rest_bucket"])["xG"]
    .mean()
    .reset_index()
    .pivot(index="playerTeam", columns="rest_bucket", values="xG")
    .reindex(columns=rest_order)
    .fillna(0)
)

ranking["Fatigue Impact (0 → 3+)"] = ranking["3+"] - ranking["0"]
ranking = ranking.sort_values("Fatigue Impact (0 → 3+)")

st.dataframe(ranking.style.format("{:.3f}"))


st.caption("📊 Data sourced from MoneyPuck.com — powered by `nhlRestEffects`.")


