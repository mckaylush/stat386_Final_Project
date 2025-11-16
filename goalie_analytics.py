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

    mode = st.sidebar.radio("Mode", ["Single Goalie View", "Compare Two Goalies"])

    goalies = sorted(df["name"].unique())
    teams = sorted(df["team"].unique())
    seasons = sorted(df["season"].unique())
    situations = sorted(df["situation"].unique())

    # Universal Filters
    selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
    selected_situation = st.sidebar.selectbox("Game Situation", ["All"] + situations)

    # Single or Two Goalies
    selected_goalie = st.sidebar.selectbox("Primary Goalie", goalies)

    if mode == "Compare Two Goalies":
        selected_goalie_2 = st.sidebar.selectbox("Compare With", [g for g in goalies if g != selected_goalie])
    else:
        selected_goalie_2 = None

    # ---------------------- COLOR MAP ----------------------
    color_map = {
        "all": "#1f77b4",
        "5on5": "#2ca02c",
        "5on4": "#9467bd",
        "4on5": "#d62728",
        "other": "#ff7f0e",
    }

    # ---------------------- FILTERING FUNCTION ----------------------
    def filter_goalie(name):
        g = df[df["name"] == name].copy()

        if selected_season != "All Seasons":
            g = g[g["season"] == selected_season]

        if selected_situation != "All":
            g = g[g["situation"] == selected_situation]

        g["save_pct"] = 1 - (g["goals"] / g["xOnGoal"])
        g["GSAx"] = g["xGoals"] - g["goals"]
        g["color"] = g["situation"].apply(lambda x: color_map.get(str(x).lower(), "#7f7f7f"))

        return g

    goalie1 = filter_goalie(selected_goalie)
    goalie2 = filter_goalie(selected_goalie_2) if selected_goalie_2 else None

    # ---------------------- HEADER ----------------------
    if mode == "Single Goalie View":
        st.header(f"📌 Goalie: {selected_goalie}")
    else:
        st.header(f"⚔️ Comparison: {selected_goalie} vs {selected_goalie_2}")

    if goalie1.empty:
        st.warning("No data available for selected filters.")
        return

    # ---------------------- SUMMARY TABLE(S) ----------------------
    def generate_summary(g):
        return {
            "Games Played": g["games_played"].sum(),
            "Shots Faced": g["xOnGoal"].sum(),
            "Goals Allowed": g["goals"].sum(),
            "Expected Goals (xGA)": round(g["xGoals"].sum(), 2),
            "Save %": f"{(1 - g['goals'].sum() / g['xOnGoal'].sum()):.3f}",
            "GSAx Total": round(g['GSAx'].sum(), 2),
        }

    st.subheader("📊 Summary Statistics")

    if mode == "Single Goalie View":
        st.dataframe(pd.DataFrame(generate_summary(goalie1), index=[0]))

    else:
        comparison_df = pd.DataFrame(
            [generate_summary(goalie1), generate_summary(goalie2)],
            index=[selected_goalie, selected_goalie_2]
        )
        st.dataframe(comparison_df)

    # ---------------------- CHARTS ----------------------
    st.subheader("📈 GSAx Over Time")

# ---- Compute metrics before plotting ----
    for g in [goalie1, goalie2] if goalie2 is not None else [goalie1]:
        g["save_pct"] = 1 - (g["goals"] / g["xOnGoal"])
        g["GSAx"] = g["xGoals"] - g["goals"]

    fig, ax = plt.subplots(figsize=(12, 5))

    def plot_trend(g, label):
        if "gameDate" in g.columns and g["gameDate"].notna().any():
            g = g.sort_values("gameDate")
            ax.plot(
                g["gameDate"], 
                g["GSAx"], 
                marker="o", 
                linewidth=2, 
                label=label
            )

    plot_trend(goalie1, selected_goalie)

    if goalie2 is not None:
        plot_trend(goalie2, selected_goalie_2)

    ax.axhline(0, linestyle="--", color="gray")
    ax.set_ylabel("GSAx (Goals Saved Above Expected)")
    ax.grid(True, alpha=0.3)
    ax.legend()

    st.pyplot(fig)


    # ---------------------- XG vs Goals Scatter ----------------------
    st.subheader("🥅 Expected vs Actual Goals Allowed")

    fig2, ax2 = plt.subplots(figsize=(8, 5))

    def scatter(g, label):
        ax2.scatter(g["xGoals"], g["goals"], s=70, alpha=0.8, label=label)

    scatter(goalie1, selected_goalie)
    if goalie2 is not None:
        scatter(goalie2, selected_goalie_2)

    ax2.plot([0, df["xGoals"].max()], [0, df["goals"].max()], linestyle="--", color="gray")
    ax2.set_xlabel("Expected Goals Allowed (xGA)")
    ax2.set_ylabel("Actual Goals Allowed")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    st.pyplot(fig2)

    st.markdown("---")
    st.caption("Data source: MoneyPuck.com")
