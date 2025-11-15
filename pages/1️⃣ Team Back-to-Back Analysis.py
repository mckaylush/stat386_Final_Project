import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="NHL Team Statistics Since 2016", layout="wide")

# ---------------------- FUNCTIONS ----------------------

def get_team_logo_url(team_abbrev):
    """
    Get NHL team logo from the official NHL assets CDN.
    Uses pattern: https://assets.nhle.com/logos/nhl/svg/[TEAM]_light.svg
    """
    clean = team_abbrev.replace(".", "").upper()
    return f"https://assets.nhle.com/logos/nhl/svg/{clean}_light.svg"



def clean_team_abbrev(abbrev):
    mapping = {
        "T.B.": "TBL",
        "TB": "TBL",
        "TAM": "TBL",

        "S.J.": "SJS",
        "SJ": "SJS",
        "SAN": "SJS",

        "N.J.": "NJD",
        "NJ": "NJD",
        "NJ DEVILS": "NJD",

        "L.A.": "LAK",
        "LA": "LAK",
        "LOS": "LAK",

        "M.T.L.": "MTL",
        "MTL.": "MTL",

        "N.Y.I.": "NYI",
        "N.Y.R.": "NYR",

        "W.P.G.": "WPG",
        "V.G.K.": "VGK",
    }
    abbrev = abbrev.strip()
    return mapping.get(abbrev, abbrev.replace(".", "").upper())

# ---------------------- LOAD + PROCESS DATA ----------------------
@st.cache_data
def load_and_process_data(path):
    df = pd.read_csv(path)
    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)
    df["opposingTeam"] = df["opposingTeam"].apply(clean_team_abbrev)


    # Team-level 5v5 only
    df = df[(df["position"] == "Team Level") & (df["situation"] == "all")].copy()

    # Dates
    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d")
    df = df[df["gameDate"].dt.year >= 2016]

    # Sort for sequencing
    df = df.sort_values(by=["playerTeam", "gameDate"]).reset_index(drop=True)

    # Rename & compute xG%
    df.rename(columns={"xGoalsFor": "xGF", "xGoalsAgainst": "xGA"}, inplace=True)
    df["xG%"] = (df["xGF"] / (df["xGF"] + df["xGA"])) * 100

    # Rest days & B2B
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days
    df["back_to_back"] = (df["days_rest"] == 1).fillna(False)

    # Win/loss flag
    df["win"] = df["goalsFor"] > df["goalsAgainst"]

    # Season label (e.g., 2016–2017)
    df["season_label"] = df["season"].astype(str)

    return df

# ---------------------- LOAD DATA ----------------------
DATA_PATH = "all_teams.csv"
df = load_and_process_data(DATA_PATH)

# ---------------------- SIDEBAR FILTERS ----------------------

st.sidebar.header("Filters")

team_list = sorted(df["playerTeam"].unique())
mode = st.sidebar.radio("Mode", ["Team", "League-wide"])

if mode == "Team":
    team_list = sorted(df["playerTeam"].unique())
    selected_team = st.sidebar.selectbox("Select Team", team_list)
else:
    selected_team = None  # no team selected in league mode

# Season options
season_options = ["All Seasons (2016–Present)"] + sorted(df["season_label"].unique())
selected_season = st.sidebar.selectbox("Select Season", season_options)

metric_mode = st.sidebar.radio(
    "Metric",
    ["Raw xGF/xGA", "Expected Goals Percentage (xG%)", "Actual vs Expected Goals"]
)

rolling_window = st.sidebar.selectbox("Rolling Average", [1, 5, 10], index=0)

home_away = st.sidebar.radio("Home/Away Split", ["All Games", "Home Only", "Away Only"])

# ---------------------- FILTER TEAM DATA ----------------------

if mode == "Team":
    team_df = df[df["playerTeam"] == selected_team].copy()
else:
    team_df = df.copy()   # entire league

if home_away == "Home Only":
    team_df = team_df[team_df["home_or_away"] == "HOME"]
elif home_away == "Away Only":
    team_df = team_df[team_df["home_or_away"] == "AWAY"]

if selected_season != "All Seasons (2016–Present)":
    team_df = team_df[team_df["season_label"] == selected_season]

team_df = team_df.reset_index(drop=True)
team_df["Game Number"] = team_df.index + 1
team_df["gameDate"] = team_df["gameDate"].dt.date

# Rolling averages
if rolling_window > 1:
    team_df["xGF_roll"]  = team_df["xGF"].rolling(rolling_window).mean()
    team_df["xGA_roll"]  = team_df["xGA"].rolling(rolling_window).mean()
    team_df["xG%_roll"]  = team_df["xG%"].rolling(rolling_window).mean()
    team_df["GF_roll"]   = team_df["goalsFor"].rolling(rolling_window).mean()
    team_df["GA_roll"]   = team_df["goalsAgainst"].rolling(rolling_window).mean()

# ---------------------- HEADER (WITH LOGO) ----------------------

if mode == "Team":
    logo_url = get_team_logo_url(selected_team)

    col1, col2 = st.columns([1, 10])
    with col1:
        st.image(logo_url, width=80)
    with col2:
        st.header(f"{selected_team} — {metric_mode}")

else:
    st.header("League-wide Back-to-Back Summary")


# ---------------------- DATA PREVIEW ----------------------
if mode == "Team":
    st.subheader("Data Preview")

    preview_cols = [
        "season_label", "opposingTeam", "gameDate",
        "xG%", "xGA",
        "goalsFor", "goalsAgainst",
        "win",
        "days_rest", "back_to_back", "Game Number"
    ]

    preview_cols = [c for c in preview_cols if c in team_df.columns]

    st.dataframe(team_df[preview_cols].head(10))


# ---------------------- MAIN CHART ----------------------
if mode == "Team":
    if selected_season == "All Seasons (2016–Present)":
        st.info("Select an individual season to view the game-by-game chart. \
                Chart hidden to avoid overcrowding (800+ games).")

    else:
        fig, ax = plt.subplots(figsize=(14, 7))

        x = team_df["Game Number"]

    # ---------------------- MAIN METRIC PLOTTING ----------------------
        if metric_mode == "Raw xGF/xGA":

        # Force smoothing of at least 3 games for visual clarity
            smoothing = max(rolling_window, 3)

            y1 = team_df["xGF"].rolling(smoothing).mean()
            y2 = team_df["xGA"].rolling(smoothing).mean()
            diff = (team_df["xGF"] - team_df["xGA"]).rolling(smoothing).mean()

        # Plot main lines
            ax.plot(x, y1, label="xGF", linewidth=2.2, color="#1f77b4")
            ax.plot(x, y2, label="xGA", linewidth=2.2, color="#ff7f0e")

        # Update y-label
            ylabel = "Expected Goals (Smoothed)"

        elif metric_mode == "Expected Goals Percentage (xG%)":

        # ----- MAIN AXIS (xG%) -----
            y = team_df["xG%_roll"] if rolling_window > 1 else team_df["xG%"]
            ax.plot(x, y, label="xG%", linewidth=2.5, color="#1f77b4")
            ylabel = "xG%"

        # Add season average line
            avg_xg_pct = y.mean()
            ax.axhline(avg_xg_pct, color="#1f77b4", linestyle="--", linewidth=1.5, alpha=0.6)
            ax.text(
                x.iloc[-1] + 0.3, avg_xg_pct, 
                f"Avg {avg_xg_pct:.1f}%", 
                color="#1f77b4", fontsize=11, va="center"
        )

        # ----- SECONDARY AXIS (Goals) -----
            ax2 = ax.twinx()

            goals = team_df["goalsFor"]
            colors = ["green" if w else "red" for w in team_df["win"]]

            ax2.scatter(
                x, goals,
                color=colors, s=40, alpha=0.9, edgecolor="black",
                label="Goals"
            )

            ax2.set_ylabel("Goals For", fontsize=12)
            ax2.set_ylim(0, max(goals) + 1)

        # Add value labels ABOVE each goal marker
            for game_num, g, c in zip(x, goals, colors):
                ax2.text(
                    game_num, g + 0.2,
                    str(g), fontsize=9,
                    ha="center", va="bottom", color=c
                )


        else:  # Actual vs Expected
            smoothing = max(rolling_window, 3)

        # Smoothed values
            gf = team_df["goalsFor"].rolling(smoothing).mean()
            ga = team_df["goalsAgainst"].rolling(smoothing).mean()
            xgf = team_df["xGF"].rolling(smoothing).mean()

        # ---- PLOT GOALS FOR / AGAINST ----
            ax.plot(x, gf, label="Goals For", linewidth=2, color="#1f77b4")
            ax.plot(x, ga, label="Goals Against", linewidth=2, color="#ff7f0e")

        # ---- PLOT xGF AS A SHADED REGION ----
            ax.fill_between(
                x, xgf - 0.25, xgf + 0.25,
                color="#2ca02c", alpha=0.25, label="xGF (smoothed band)"
        )
            ax.plot(x, xgf, color="#2ca02c", linewidth=1.6, linestyle="--")

            ylabel = "Goals"

        # ---- WIN/LOSS MARKERS ON TOP (clean) ----
        for idx, row in team_df.iterrows():
            color = "green" if row["win"] else "red"
            ax.scatter(
                row["Game Number"], row["goalsFor"],
                color=color, s=45, alpha=0.9, edgecolor="black", zorder=10
            )


    # ---------------------- HIGHLIGHT 2ND BACK TO BACK GAME----------------------
        b2b_game2 = team_df[team_df["days_rest"] == 1]["Game Number"].tolist()
        for gnum in b2b_game2:
            ax.axvspan(gnum - 0.5, gnum + 0.5, color="#e8e8e8", alpha=0.6)

    # ---------------------- WIN/LOSS MARKERS ----------------------
        if metric_mode != "Expected Goals Percentage (xG%)":
            for idx, row in team_df.iterrows():
                color = "green" if row["win"] else "red"
                y_val = (
                    row["GF_roll"] if (metric_mode == "Actual vs Expected" and rolling_window > 1)
                    else row["goalsFor"]
                )
                ax.scatter(
                row["Game Number"], y_val,
                    color=color, s=50, alpha=0.8, edgecolor="black"
                )

            # ---------------------- ADD GOALS SCORED LABEL ----------------------
            
            if metric_mode == "Expected Goals Percentage (xG%)":
                # label actual goals on the xG% chart
                ax.text(
                    game_num, y_val + 0.3,
                    str(row["goalsFor"]),
                    fontsize=9, ha="center", va="bottom"
                )


    # ---------------------- STYLE IMPROVEMENTS ----------------------
        ax.set_xlabel("Game Number", fontsize=13)
        ax.set_ylabel(ylabel, fontsize=13)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=12)
        ax.tick_params(axis="both", labelsize=11)

        st.pyplot(fig)


# ---------------------- BACK-TO-BACK SUMMARY ----------------------

st.header("Back-to-Back Performance Summary")

b2b = team_df[team_df["back_to_back"] == True]
nonb2b = team_df[team_df["back_to_back"] == False]

if not b2b.empty and not nonb2b.empty:
    b2b_stats = b2b[["xGF", "xGA", "goalsFor", "goalsAgainst"]].mean().rename("Back-to-Back")
    nb2b_stats = nonb2b[["xGF", "xGA", "goalsFor", "goalsAgainst"]].mean().rename("Non-B2B")
    summary = pd.concat([nb2b_stats, b2b_stats], axis=1).T
    st.dataframe(summary)
else:
    st.warning("No back-to-back games available in this filtered dataset.")

# ---------------------- FIRST GAME vs SECOND GAME OF B2B ----------------------

# Identify B2B pairs
team_df["next_days_rest"] = team_df["days_rest"].shift(-1)

b2b_pairs = []
for i in range(len(team_df) - 1):
    # A back-to-back pair is when the NEXT game has 1 day rest
    if team_df.loc[i + 1, "days_rest"] == 1:
        game1 = team_df.loc[i]
        game2 = team_df.loc[i + 1]
        b2b_pairs.append((game1, game2))

if len(b2b_pairs) == 0:
    st.warning("No full back-to-back sets found for this team and season.")
else:
    # Build a DataFrame comparing the two games
    data = {
        "Game Type": [],
        "xGF": [],
        "xGA": [],
        "xG%": [],
        "Goals For": [],
        "Goals Against": []
    }

    for game1, game2 in b2b_pairs:
        # First game
        data["Game Type"].append("B2B Game 1")
        data["xGF"].append(game1["xGF"])
        data["xGA"].append(game1["xGA"])
        data["xG%"].append(game1["xG%"])
        data["Goals For"].append(game1["goalsFor"])
        data["Goals Against"].append(game1["goalsAgainst"])

        # Second game
        data["Game Type"].append("B2B Game 2")
        data["xGF"].append(game2["xGF"])
        data["xGA"].append(game2["xGA"])
        data["xG%"].append(game2["xG%"])
        data["Goals For"].append(game2["goalsFor"])
        data["Goals Against"].append(game2["goalsAgainst"])

    compare_df = pd.DataFrame(data)

    st.subheader("B2B Game 1 vs Game 2 Averages")
    avg_df = compare_df.groupby("Game Type").mean()
    st.dataframe(avg_df)

    # Visualization
st.subheader("Visualization")

# Combine all metrics into one chart
combined = avg_df[["xGF", "xGA", "Goals For", "Goals Against"]]

fig_combined, ax_combined = plt.subplots(figsize=(12, 6))

combined.plot(kind="bar", ax=ax_combined)

ax_combined.set_title("B2B Game 1 vs Game 2 — Expected & Actual Goals Comparison")
ax_combined.set_ylabel("Goals / Expected Goals")
ax_combined.grid(True, alpha=0.3)
ax_combined.legend(title="Metric")

st.pyplot(fig_combined)

st.markdown("""The data for this dashboard was sourced from MoneyPuck.com and we thank them for their contributions and ability to collect data.""")
