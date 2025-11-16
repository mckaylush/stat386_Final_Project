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

# ---------------------- NHL HEADSHOT URL ----------------------
def get_headshot_url(player_id):
    if pd.isna(player_id):
        return None  # prevent errors if missing
    return f"https://assets.nhle.com/mugs/nhl/{int(player_id)}.png"

def get_team_logo(team_abbrev):
    return f"https://assets.nhle.com/logos/nhl/svg/{team_abbrev.upper()}_light.svg"

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

    selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
    selected_situation = st.sidebar.selectbox("Game Situation", ["All"] + situations)

    selected_goalie = st.sidebar.selectbox("Primary Goalie", goalies)

    if mode == "Compare Two Goalies":
        selected_goalie_2 = st.sidebar.selectbox("Compare With", [g for g in goalies if g != selected_goalie])
    else:
        selected_goalie_2 = None

    # ---------------------- FILTERING FUNCTION ----------------------
    def filter_goalie(name):
        g = df[df["name"] == name].copy()

        if selected_season != "All Seasons":
            g = g[g["season"] == selected_season]

        if selected_situation != "All":
            g = g[g["situation"] == selected_situation]

        g["GSAx"] = g["xGoals"] - g["goals"]
        g["save_pct"] = 1 - (g["goals"] / g["xOnGoal"])
        return g

    goalie1 = filter_goalie(selected_goalie)
    goalie2 = filter_goalie(selected_goalie_2) if selected_goalie_2 else None

    # ---------------------- HEADER SECTION ----------------------
    if mode == "Single Goalie View":
        st.header(f"📌 Goalie: {selected_goalie}")

        # Profile card layout
        col_img, col_info = st.columns([1, 3])

        with col_img:
            try:
                headshot = get_headshot_url(goalie1["playerId"].iloc[0])
                st.image(headshot, width=180)
            except:
                st.write("(No photo available)")

        with col_info:
            st.write(f"**Team(s):** {', '.join(sorted(goalie1['team'].unique()))}")
            st.write(f"**Seasons:** {', '.join(sorted(goalie1['season'].astype(str).unique()))}")
            st.write(f"**Situation Filter:** {selected_situation}")

    else:
        st.header(f"⚔️ Comparison: {selected_goalie} vs {selected_goalie_2}")

        colA, colB = st.columns(2)

        # Left goalie
        with colA:
            try:
                st.image(get_headshot_url(goalie1["playerId"].iloc[0]), width=180)
            except:
                st.write("(No photo)")

            st.markdown(f"### {selected_goalie}")

        # Right goalie
        with colB:
            try:
                st.image(get_headshot_url(goalie2["playerId"].iloc[0]), width=180)
            except:
                st.write("(No photo)")
            st.markdown(f"### {selected_goalie_2}")

    if goalie1.empty:
        st.warning("No data available for selected filters.")
        return

    # ---------------------- SUMMARY TABLE SECTION ----------------------
    def generate_summary(g):
        games_by_season = g.groupby("season")["games_played"].max()
        total_games_played = int(games_by_season.sum())

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
            "Save %": f"{save_pct:.3f}",
            "Total GSAx": round(gsax_total, 2),
        }

    st.subheader("📊 Summary Statistics")

    if mode == "Single Goalie View":
        st.dataframe(pd.DataFrame(generate_summary(goalie1), index=[0]))
    else:
        st.dataframe(pd.DataFrame(
            [generate_summary(goalie1), generate_summary(goalie2)],
            index=[selected_goalie, selected_goalie_2]
        ))

    # ---------------------- GSAx PER SEASON BAR CHART ----------------------
    st.subheader("📊 GSAx by Season")

    g1_season = goalie1.groupby("season", as_index=False)["GSAx"].sum()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(g1_season["season"].astype(str), g1_season["GSAx"], label=selected_goalie)

    if goalie2 is not None:
        g2_season = goalie2.groupby("season", as_index=False)["GSAx"].sum()
        ax.bar(g2_season["season"].astype(str), g2_season["GSAx"], label=selected_goalie_2, alpha=0.6)

    ax.axhline(0, linestyle="--", color="gray")
    ax.set_ylabel("Total GSAx")
    ax.set_title("Goals Saved Above Expected (Season Total)")
    ax.grid(True, alpha=0.3)
    ax.legend()

    st.pyplot(fig)

    # ---------------------- XGA vs GOALS SCATTER ----------------------
    st.subheader("🥅 Expected vs Actual Goals Allowed")

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.scatter(goalie1["xGoals"], goalie1["goals"], s=80, label=selected_goalie)

    if goalie2 is not None:
        ax2.scatter(goalie2["xGoals"], goalie2["goals"], s=80, label=selected_goalie_2)

    ax2.plot([0, df["xGoals"].max()], [0, df["goals"].max()], linestyle="--", color="gray")
    ax2.set_xlabel("Expected Goals Against (xGA)")
    ax2.set_ylabel("Actual Goals Allowed")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    st.pyplot(fig2)

    st.markdown("---")
    st.caption("Data source: MoneyPuck.com")

