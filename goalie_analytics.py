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
    seasons = sorted(df["season"].unique())
    situations = sorted(df["situation"].unique())

    # Universal filters
    selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
    selected_situation = st.sidebar.selectbox("Game Situation", ["All"] + situations)

    # Goalie selection
    selected_goalie = st.sidebar.selectbox("Primary Goalie", goalies)

    if mode == "Compare Two Goalies":
        compare_choices = [g for g in goalies if g != selected_goalie]
        selected_goalie_2 = st.sidebar.selectbox("Compare With", compare_choices)
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
    def filter_goalie(name: str) -> pd.DataFrame:
        g = df[df["name"] == name].copy()

        if selected_season != "All Seasons":
            g = g[g["season"] == selected_season]

        if selected_situation != "All":
            g = g[g["situation"] == selected_situation]

        if g.empty:
            return g

        # Core metrics
        g["save_pct"] = 1 - (g["goals"] / g["xOnGoal"])
        g["GSAx"] = g["xGoals"] - g["goals"]
        g["color"] = g["situation"].apply(
            lambda x: color_map.get(str(x).lower(), "#7f7f7f")
        )
        return g

    goalie1 = filter_goalie(selected_goalie)
    goalie2 = filter_goalie(selected_goalie_2) if selected_goalie_2 else None

    # ---------------------- HEADER ----------------------
    if mode == "Single Goalie View":
        st.header(f"📌 Goalie: {selected_goalie}")
    else:
        st.header(f"⚔️ Comparison: {selected_goalie} vs {selected_goalie_2}")

    if goalie1.empty:
        st.warning("No data available for the selected filters.")
        return

    # ---------------------- SUMMARY TABLE(S) ----------------------
    def generate_summary(g: pd.DataFrame):
        # Fix games-played inflation: games_played is repeated by situation.
        if "games_played" in g.columns:
            games_by_season = g.groupby("season")["games_played"].max()
            total_games_played = int(games_by_season.sum())
        else:
            total_games_played = None

        shots_faced = g["xOnGoal"].sum()
        goals_allowed = g["goals"].sum()
        xga_total = g["xGoals"].sum()
        gsax_total = g["GSAx"].sum()

        save_pct = 1 - (goals_allowed / shots_faced) if shots_faced > 0 else float("nan")

        return {
            "Games Played": total_games_played,
            "Shots Faced": int(shots_faced),
            "Goals Allowed": int(goals_allowed),
            "Expected Goals (xGA)": round(xga_total, 2),
            "Save %": f"{save_pct:.3f}" if shots_faced > 0 else "N/A",
            "GSAx Total": round(gsax_total, 2),
        }

    st.subheader("📊 Summary Statistics")

    if mode == "Single Goalie View":
        summary_df = pd.DataFrame(generate_summary(goalie1), index=[0])
        st.dataframe(summary_df, use_container_width=True)
    else:
        if goalie2 is None or goalie2.empty:
            st.warning("No data available for comparison goalie with these filters.")
        else:
            comparison_df = pd.DataFrame(
                [generate_summary(goalie1), generate_summary(goalie2)],
                index=[selected_goalie, selected_goalie_2],
            )
            st.dataframe(comparison_df, use_container_width=True)

    # ---------------------- GSAx BY SEASON ----------------------
    st.subheader("📊 GSAx by Season")

    # Aggregate GSAx per season for each goalie
    g1_season = (
        goalie1.groupby("season", as_index=False)["GSAx"]
        .sum()
        .rename(columns={"GSAx": selected_goalie})
    )

    if goalie2 is not None and not goalie2.empty:
        g2_season = (
            goalie2.groupby("season", as_index=False)["GSAx"]
            .sum()
            .rename(columns={"GSAx": selected_goalie_2})
        )
        season_df = pd.merge(g1_season, g2_season, on="season", how="outer").fillna(0)
    else:
        season_df = g1_season.copy()

    if season_df.empty:
        st.warning("No seasonal GSAx data available.")
    else:
        season_df = season_df.sort_values("season")
        seasons = season_df["season"].astype(str).tolist()
        x = range(len(seasons))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 5))

        # Primary goalie bars
        ax.bar(
            [i - width / 2 for i in x],
            season_df[selected_goalie],
            width=width,
            label=selected_goalie,
            color="#1f77b4",
        )

        # Comparison goalie bars
        if goalie2 is not None and not goalie2.empty:
            ax.bar(
                [i + width / 2 for i in x],
                season_df[selected_goalie_2],
                width=width,
                label=selected_goalie_2,
                color="#d62728",
            )

        ax.axhline(0, linestyle="--", color="gray")
        ax.set_xticks(list(x))
        ax.set_xticklabels(seasons)
        ax.set_ylabel("Total GSAx")
        ax.set_xlabel("Season")
        ax.set_title("Goals Saved Above Expected by Season")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)

    # ---------------------- XG vs GOALS SCATTER (COLORED) ----------------------
    st.subheader("🥅 Expected vs Actual Goals Allowed (Colored by Situation)")

    fig2, ax2 = plt.subplots(figsize=(8, 5))

    # Goalie 1 points
    for situation, group in goalie1.groupby("situation"):
        ax2.scatter(
            group["xGoals"],
            group["goals"],
            s=70,
            alpha=0.8,
            label=f"{situation} – {selected_goalie}",
            color=color_map.get(str(situation).lower(), "#7f7f7f"),
        )

    # Goalie 2 points (if comparison)
    if goalie2 is not None and not goalie2.empty:
        for situation, group in goalie2.groupby("situation"):
            ax2.scatter(
                group["xGoals"],
                group["goals"],
                s=70,
                alpha=0.8,
                marker="^",  # triangle for comparison goalie
                label=f"{situation} – {selected_goalie_2}",
                color=color_map.get(str(situation).lower(), "#7f7f7f"),
            )

    max_val = max(df["xGoals"].max(), df["goals"].max())
    ax2.plot([0, max_val], [0, max_val], linestyle="--", color="gray", label="Expected = Actual")

    ax2.set_xlabel("Expected Goals Allowed (xGA)")
    ax2.set_ylabel("Actual Goals Allowed")
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=8)
    st.pyplot(fig2)

    st.markdown("---")
    st.caption("Data source: MoneyPuck.com")
