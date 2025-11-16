import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_goalie_data(path="data/goalies_allseasons.csv"):
    df = pd.read_csv(path)

    # Fix timestamp if included
    if "gameDate" in df.columns:
        df["gameDate"] = pd.to_datetime(df["gameDate"], errors="ignore")

    return df


# ---------------------- PAGE FUNCTION ----------------------
def goalie_analytics_page():

    st.title("🎯 NHL Goalie Analytics Dashboard")

    df = load_goalie_data()

    # ---------------------- SIDEBAR FILTERS ----------------------
    st.sidebar.header("Filters")

    goalies = sorted(df["name"].unique())
    teams = sorted(df["team"].unique())
    seasons = sorted(df["season"].unique())
    situations = sorted(df["situation"].unique())

    selected_goalie = st.sidebar.selectbox("Select Goalie", ["All Goalies"] + goalies)
    selected_team = st.sidebar.selectbox("Filter by Team", ["All Teams"] + teams)
    selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
    selected_situation = st.sidebar.selectbox("Game Situation", ["All"] + situations)

    # ---------------------- APPLY FILTERS ----------------------
    filtered = df.copy()

    if selected_goalie != "All Goalies":
        filtered = filtered[filtered["name"] == selected_goalie]

    if selected_team != "All Teams":
        filtered = filtered[filtered["team"] == selected_team]

    if selected_season != "All Seasons":
        filtered = filtered[filtered["season"] == selected_season]

    if selected_situation != "All":
        filtered = filtered[filtered["situation"] == selected_situation]

    filtered = filtered.reset_index(drop=True)

    # Color mapping for situations
    color_map = {
    "all": "#1f77b4",
    "5v5": "#2ca02c",
    "pp": "#d62728",
    "pk": "#9467bd",
}

    # Assign a default if a new situation appears
    filtered["color"] = filtered["situation"].apply(lambda x: color_map.get(str(x).lower(), "#7f7f7f"))

    # ---------------------- HEADER ----------------------
    if selected_goalie != "All Goalies":
        st.header(f"📌 Goalie: {selected_goalie}")
    else:
        st.header("📌 League Overview")

    if filtered.empty:
        st.warning("No matching records.")
        return

    # ---------------------- METRICS ----------------------
    filtered["save_pct"] = 1 - (filtered["goals"] / filtered["xOnGoal"])
    filtered["GSAx"] = filtered["xGoals"] - filtered["goals"]

    summary = {
        "Games Played": filtered["games_played"].sum(),
        "Total Shots Faced": filtered["xOnGoal"].sum(),
        "Goals Allowed": filtered["goals"].sum(),
        "Expected Goals Against (xGA)": round(filtered["xGoals"].sum(), 2),
        "Save %": f"{(1 - filtered['goals'].sum() / filtered['xOnGoal'].sum()):.3f}",
        "Goals Saved Above Expected (GSAx)": round(filtered["GSAx"].sum(), 2),
    }

    st.subheader("📊 Summary Metrics")
    st.write(pd.DataFrame(summary, index=[0]))

    # ---------------------- CHARTS ----------------------

    # ⭐ 1: Trend GSAx Over Time
    i# ⭐ 1: Trend GSAx Over Time with color-coded situations
    if "gameDate" in filtered.columns and filtered["gameDate"].notna().any():
        st.subheader("📈 GSAx Trend Over Time (Colored by Situation)")

        filtered = filtered.sort_values("gameDate")
        fig1, ax1 = plt.subplots(figsize=(12, 5))

        for situation, group in filtered.groupby("situation"):
            ax1.plot(
                group["gameDate"], 
                group["GSAx"], 
                marker="o", 
                linewidth=2,
                label=situation, 
                color=color_map.get(str(situation).lower(), "#7f7f7f")
            )

        ax1.axhline(0, color="gray", linestyle="--")
        ax1.set_ylabel("Goals Saved Above Expected")
        ax1.grid(True, alpha=0.3)
        ax1.legend(title="Game Situation")

        st.pyplot(fig1)


    # ⭐ 2: Shot Danger Breakdown
    st.subheader("🎯 Shot Danger Breakdown")

    danger_cols = ["lowDangerShots", "mediumDangerShots", "highDangerShots",
                   "lowDangerGoals", "mediumDangerGoals", "highDangerGoals"]

    if all(col in filtered.columns for col in danger_cols):
        groups = {
            "Low Danger": [filtered["lowDangerShots"].sum(), filtered["lowDangerGoals"].sum()],
            "Medium Danger": [filtered["mediumDangerShots"].sum(), filtered["mediumDangerGoals"].sum()],
            "High Danger": [filtered["highDangerShots"].sum(), filtered["highDangerGoals"].sum()],
        }

        danger_df = pd.DataFrame(groups, index=["Shots Faced", "Goals Allowed"]).T
        st.dataframe(danger_df, use_container_width=True)

        fig2, ax2 = plt.subplots(figsize=(8, 5))
        danger_df["Goals Allowed"].plot(kind="bar", ax=ax2)
        ax2.set_ylabel("Goals")
        ax2.set_title("Goals Allowed by Shot Type")
        ax2.grid(True, alpha=0.3)
        st.pyplot(fig2)

    # ⭐ 3: Expected vs Actual Goals Colored by Situation
    st.subheader("🥅 Expected vs Actual Goals Allowed (Colored by Situation)")

    fig3, ax3 = plt.subplots(figsize=(8, 5))

    for situation, group in filtered.groupby("situation"):
        ax3.scatter(
            group["xGoals"],
            group["goals"],
            s=70,
            alpha=0.8,
            label=situation,
            color=color_map.get(str(situation).lower(), "#7f7f7f")
        )

    ax3.plot(
        [0, max(filtered["xGoals"])],
        [0, max(filtered["goals"])],
        linestyle="--",
        color="gray",
        label="Expected=Actual Line"
    )

    ax3.set_xlabel("Expected Goals (xGA)")
    ax3.set_ylabel("Actual Goals Allowed")
    ax3.grid(True, alpha=0.3)
    ax3.legend(title="Game Situation")

    st.pyplot(fig3)


    st.markdown("---")
    st.caption("Data source: MoneyPuck.com")
