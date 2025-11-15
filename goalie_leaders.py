import streamlit as st
import pandas as pd

@st.cache_data
def load_goalie_data():
    return pd.read_csv("data/goalies_allseasons.csv")

def leaderboard_page():
    df = load_goalie_data()

    st.title("🥅 Goalie Leaderboard")

    # Filters
    season = st.selectbox("Season", ["All"] + sorted(df["season"].unique()))
    if season != "All":
        df = df[df["season"] == season]

    # Metrics to compare
    metric = st.selectbox("Sort By:", [
        "xGoals",
        "goals",
        "save_percent",
        "danger_diff",
        "highDangerGoals",
        "mediumDangerGoals",
        "lowDangerGoals"
    ])

    # Compute added metrics if not in dataset
    if "save_percent" not in df.columns:
        df["save_percent"] = 1 - (df["goals"] / df["xGoals"])
    if "danger_diff" not in df.columns:
        df["danger_diff"] = df["xGoals"] - df["goals"]

    # Sort and show top/bottom
    st.subheader(f"Top Goalies — {metric}")
    st.dataframe(df.sort_values(metric, ascending=metric!="goals").head(15))

    st.subheader(f"Bottom Goalies — {metric}")
    st.dataframe(df.sort_values(metric, ascending=metric=="goals").head(15))
