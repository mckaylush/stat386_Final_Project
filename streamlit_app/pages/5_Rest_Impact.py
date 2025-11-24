import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import (
    convert_numeric_columns,
    add_game_numbers,
    add_rolling_metrics
)

# ---------------------- PAGE ----------------------
st.title("⏱️ Rest Impact on Team Performance")

@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv")  
    df = convert_numeric_columns(df)
    df = add_game_numbers(df)
    df = add_rolling_metrics(df)
    return df

df = cached_rest_data()

# ---------------------- FILTERS ----------------------
teams = sorted(df["team"].unique())
seasons = sorted(df["season"].unique())

selected_team = st.sidebar.selectbox("Team:", teams)
selected_season = st.sidebar.selectbox("Season:", ["All"] + seasons)

filtered = df[df["team"] == selected_team].copy()
if selected_season != "All":
    filtered = filtered[filtered["season"] == selected_season]

# ---------------------- VIEW ----------------------
st.subheader(f"📈 Rest vs Expected Goals Performance")

fig, ax = plt.subplots(figsize=(10, 5))
ax.scatter(filtered["daysRest"], filtered["xGoalsPercentage"], alpha=0.7)
ax.set_xlabel("Days of Rest")
ax.set_ylabel("Expected Goals % (xG%)")
ax.grid(alpha=0.2)

st.pyplot(fig)

# Summary Stats
avg = filtered.groupby("daysRest")["xGoalsPercentage"].mean().reset_index()
st.subheader("📋 Average xG% by Rest Days")
st.table(avg.style.format("{:.2f}"))

st.caption("Powered by nhlRestEffects package")
