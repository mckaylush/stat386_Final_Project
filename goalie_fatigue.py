import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_goalie_data(path="data/goalies_allseasons.csv"):
    df = pd.read_csv(path)

    # No gameDate column yet — this version won’t attempt rest-day logic
    return df


# ---------------------- PAGE FUNCTION ----------------------
def goalie_fatigue_page():

    st.title("🥵 Goalie Fatigue Explorer (Season-Based)")

    df = load_goalie_data()

    # -------- SIDEBAR --------
    st.sidebar.header("Filters")

    mode = st.sidebar.radio("Mode", ["Single Goalie View", "Compare Two Goalies"])

    goalies = sorted(df["name"].unique())
    seasons = sorted(df["season"].unique())
    situations = sorted(df["situation"].unique())

    selected_goalie = st.sidebar.selectbox("Primary Goalie", goalies)
    selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
    selected_situation = st.sidebar.selectbox("Game Situation", ["All"] + situations)

    if mode == "Compare Two Goalies":
        selected_goalie_2 = st.sidebar.selectbox("Compare With", [g for g in goalies if g != selected_goalie])
    else:
        selected_goalie_2 = None

    # -------- FILTERING --------
    def filter_goalie(name):
        g = df[df["name"] == name].copy()

        if selected_season != "All Seasons":
            g = g[g["season"] == selected_season]

        if selected_situation != "All":
            g = g[g["situation"] == selected_situation]

        return g

    g1 = filter_goalie(selected_goalie)
    g2 = filter_goalie(selected_goalie_2) if selected_goalie_2 else None

    if g1.empty:
        st.warning("⚠ No matching data found for this goalie/season filter.")
        return

    # -------- COMPUTE METRICS --------

    # Approximate game segments (season quarters)
    def segment(df):
        df = df.sort_values("games_played")
        df["segment"] = pd.qcut(df["games_played"], q=4, labels=["Q1", "Q2", "Q3", "Q4"])
        df["save_pct"] = 1 - (df["goals"] / df["xOnGoal"])
        df["GSAx"] = df["xGoals"] - df["goals"]
        return df

    g1 = segment(g1)
    if g2 is not None:
        g2 = segment(g2)

    # -------- DISPLAY SUMMARY --------
    st.subheader("📊 Fatigue Pattern Summary")

    def summary(df):
        return df.groupby("segment")[["save_pct", "GSAx"]].mean().round(3)

    st.write(f"📌 **{selected_goalie} Trend:**")
    st.dataframe(summary(g1))

    if g2 is not None:
        st.write(f"📌 **{selected_goalie_2} Trend:**")
        st.dataframe(summary(g2))

    # -------- CHARTS --------

    st.subheader("📈 Save Percentage Decay Curve")

    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(summary(g1).index, summary(g1)["save_pct"], marker="o", label=selected_goalie)

    if g2 is not None:
        ax1.plot(summary(g2).index, summary(g2)["save_pct"], marker="o", label=selected_goalie_2)

    ax1.set_ylabel("Save %")
    ax1.set_xlabel("Season Segment")
    ax1.set_title("Does Performance Drop Over the Season?")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    st.pyplot(fig1)

    st.subheader("📉 GSAx Trend Across Season")

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.plot(summary(g1).index, summary(g1)["GSAx"], marker="o", label=selected_goalie)

    if g2 is not None:
        ax2.plot(summary(g2).index, summary(g2)["GSAx"], marker="o", label=selected_goalie_2)

    ax2.set_ylabel("GSAx")
    ax2.set_xlabel("Season Segment")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    st.pyplot(fig2)

    st.markdown("---")
    st.caption("Future upgrade: real fatigue using per-game rest, workload, and schedule tracking.")
