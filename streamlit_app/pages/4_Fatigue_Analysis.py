import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_goalie_data
from nhlRestEffects.analysis import filter_goalie, summarize_goalie, segment_goalie_fatigue

# ---------------------- PAGE SETUP ----------------------
st.title("🥵 Goalie Fatigue Explorer")

@st.cache_data
def cached_goalies():
    return load_goalie_data()

df = cached_goalies()


# ---------------------- SIDEBAR ----------------------
st.sidebar.header("Filters")

mode = st.sidebar.radio("Mode", ["Single Goalie View", "Compare Two Goalies"])
goalies = sorted(df["name"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_goalie = st.sidebar.selectbox("Primary Goalie", goalies)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

selected_goalie_2 = (
    st.sidebar.selectbox("Compare With", [g for g in goalies if g != selected_goalie])
    if mode == "Compare Two Goalies" else None
)


# ---------------------- APPLY PACKAGE PROCESSING ----------------------
goalie1 = filter_goalie(df, selected_goalie, selected_season)
goalie1 = segment_goalie_fatigue(goalie1)

goalie2 = None
if selected_goalie_2:
    goalie2 = filter_goalie(df, selected_goalie_2, selected_season)
    goalie2 = segment_goalie_fatigue(goalie2)


# ---------------------- SUMMARY ----------------------
st.subheader("📊 Fatigue Trend Summary")

def fatigue_summary(df):
    return df.groupby("segment")[["save_pct", "GSAx"]].mean().round(3)

st.write(f"📌 **{selected_goalie} Trend:**")
st.dataframe(fatigue_summary(goalie1))

if goalie2 is not None:
    st.write(f"📌 **{selected_goalie_2} Trend:**")
    st.dataframe(fatigue_summary(goalie2))


# ---------------------- SAVE % TREND PLOT ----------------------
st.subheader("📈 Save % Across Season Segments")

fig1, ax1 = plt.subplots(figsize=(10,5))
ax1.plot(fatigue_summary(goalie1).index, fatigue_summary(goalie1)["save_pct"],
         marker="o", label=selected_goalie)

if goalie2 is not None:
    ax1.plot(fatigue_summary(goalie2).index, fatigue_summary(goalie2)["save_pct"],
             marker="o", label=selected_goalie_2)

ax1.set_ylabel("Save %")
ax1.set_xlabel("Season Segment")
ax1.grid(True, alpha=0.3)
ax1.legend()
st.pyplot(fig1)


# ---------------------- GSAx TREND ----------------------
st.subheader("📉 GSAx Across Season Segments")

fig2, ax2 = plt.subplots(figsize=(10,5))
ax2.plot(fatigue_summary(goalie1).index, fatigue_summary(goalie1)["GSAx"],
         marker="o", label=selected_goalie)

if goalie2 is not None:
    ax2.plot(fatigue_summary(goalie2).index, fatigue_summary(goalie2)["GSAx"],
             marker="o", label=selected_goalie_2)

ax2.set_ylabel("GSAx")
ax2.set_xlabel("Season Segment")
ax2.grid(True, alpha=0.3)
ax2.legend()
st.pyplot(fig2)


st.markdown("---")
st.caption("Data from MoneyPuck.com — Analysis powered by `nhlRestEffects` package.")
