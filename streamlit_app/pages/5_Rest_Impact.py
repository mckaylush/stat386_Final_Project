import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def load_data():
    # ... (Keep existing loading and column creation) ...

    # ---- Sort + compute days of rest ----
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # ---- Bin into 0,1,2,3+ ----
    def bucket(days):
        # 1. First game (NaN): Exclude from analysis by returning None.
        if pd.isna(days): 
            return None 

        # 2. True 'No Rest' (Back-to-back): days_rest will be 1 day (e.g., played Mon, next game Tue). 
        #    If you want to count 1 day of rest as '0 days rest' in hockey terms:
        #    * The difference between today and yesterday is 1 day.
        #    * A back-to-back is 0 days rest.
        #    * Let's change the logic to: 
        #      * days_rest == 1 is '0 days rest' (i.e., back-to-back)
        #      * days_rest == 2 is '1 day rest'
        #      * days_rest == 3 is '2 days rest'
        #
        #    ***However, based on your original code, you are defining rest days based on the value of the diff. 
        #    Let's stick to the numerical diff value:***

        # ORIGINAL LOGIC:
        if days <= 0: return "0" # <- All bad diffs or zero diffs go here.
        if days == 1: return "1"  # <- THIS IS THE ISSUE! A 1-day diff is a back-to-back (0 rest)
        if days == 2: return "2"
        return "3+"

    # ***REVISED BUCKET LOGIC (standard hockey rest days)***
    def new_bucket(days):
        if pd.isna(days): 
            return None # Exclude first game

        # A diff of 1 day (e.g., Mon to Tue) means 0 days off, i.e., back-to-back
        if days <= 1: 
            return "0" 
        
        # A diff of 2 days (e.g., Mon to Wed) means 1 day off
        if days == 2: 
            return "1" 

        # A diff of 3 days (e.g., Mon to Thur) means 2 days off
        if days == 3: 
            return "2"
        
        # A diff of 4+ days means 3+ days off
        if days >= 4:
            return "3+"
        
        # Catch-all for weird/negative diffs that shouldn't exist after sorting
        return None

    df["rest_bucket"] = df["days_rest"].apply(new_bucket)
    
    # NEW: Filter out the NA buckets (first games AND any bad data points)
    df = df.dropna(subset=['rest_bucket']) 

    return df
df = load_data()

# ---------------------- Sidebar ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

# ---------------------- Filter data ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()

if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

team_df = team_df.dropna(subset=["xG"])

# ---------------------- Show rest breakdown ----------------------
st.caption(f"Rest bucket counts for {selected_team}")
st.write(team_df["rest_bucket"].value_counts().sort_index())

# ---------------------- Plot ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

if team_df.empty:
    st.warning("Not enough data.")
else:
    summary = (
        team_df.groupby("rest_bucket")["xG"]
        .mean()
        .reindex(rest_order)
        .fillna(0)
    )

    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(rest_order, summary.values, edgecolor="black")

    for x, height in zip(rest_order, summary.values):
        ax.text(x, height + 0.01, f"{height:.2f}", ha="center")

    ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.5)
    ax.set_ylabel("Avg Expected Goals %")
    ax.set_xlabel("Rest Days")
    ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

    st.pyplot(fig)

# ---------------------- League-wide ranking ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking (League-wide)")

league_df = df.dropna(subset=["xG"])

if league_df.empty:
    st.warning("No league-wide data.")
else:
    league_summary = (
        league_df.groupby(["playerTeam","rest_bucket"])["xG"]
        .mean()
        .unstack()
        .reindex(columns=rest_order)
        .fillna(0)
    )

    league_summary["Fatigue Impact (0 → 3+)"] = league_summary["3+"] - league_summary["0"]
    league_summary = league_summary.sort_values("Fatigue Impact (0 → 3+)")

    st.dataframe(league_summary.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
