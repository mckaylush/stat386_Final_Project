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
selected_team = st.sidebar.selectbox("Select Team", team_list)

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

team_df = df[df["playerTeam"] == selected_team].copy()

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

logo_url = get_team_logo_url(selected_team)

col1, col2 = st.columns([1, 10])
with col1:
    st.image(logo_url, width=80)
with col2:
    st.header(f"{selected_team} — {metric_mode}")

# ---------------------- DATA PREVIEW ----------------------
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

if selected_season == "All Seasons (2016–Present)":
    st.info("Select an individual season to view the game-by-game chart. \
            Chart hidden to avoid overcrowding (800+ games).")

else:
    fig, ax = plt.subplots(figsize=(14, 7))

    x = team_df["Game Number"]

    # Main metric plotting
    if metric_mode == "Raw xGF/xGA":
        y1 = team_df["xGF_roll"] if rolling_window > 1 else team_df["xGF"]
        y2 = team_df["xGA_roll"] if rolling_window > 1 else team_df["xGA"]
        ax.plot(x, y1, label="xGF", linewidth=2.5)
        ax.plot(x, y2, label="xGA", linewidth=2.5)
        ylabel = "Expected Goals"

    elif metric_mode == "Expected Goals Percentage (xG%)":
        y = team_df["xG%_roll"] if rolling_window > 1 else team_df["xG%"]
        ax.plot(x, y, label="xG%", linewidth=2.5)
        ylabel = "xG%"

    else:  # Actual vs Expected
        y1 = team_df["GF_roll"] if rolling_window > 1 else team_df["goalsFor"]
        y2 = team_df["GA_roll"] if rolling_window > 1 else team_df["goalsAgainst"]
        y3 = team_df["xGF_roll"] if rolling_window > 1 else team_df["xGF"]
        ax.plot(x, y1, label="Goals For", linewidth=2.5)
        ax.plot(x, y2, label="Goals Against", linewidth=2.5)
        ax.plot(x, y3, label="xGF", linewidth=2.0, linestyle="--")
        ylabel = "Goals"

    # Highlight 2nd game of back-to-back (yellow bar)
    b2b_game2 = team_df[team_df["days_rest"] == 1]["Game Number"].tolist()
    for gnum in b2b_game2:
        ax.axvspan(gnum - 0.5, gnum + 0.5, color="yellow", alpha=0.2)

    # Win/loss markers
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

    # Style improvements
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
    st.bar_chart(summary)
else:
    st.warning("No back-to-back games available in this filtered dataset.")

# ---------------------- FIRST GAME vs SECOND GAME OF B2B ----------------------

st.header("First Game vs Second Game of Back-to-Back Sets")

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

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    avg_df[["xGF", "xGA"]].plot(kind="bar", ax=ax2)
    ax2.set_title("Expected Goals Comparison: B2B Game 1 vs Game 2")
    ax2.set_ylabel("Expected Goals")
    ax2.grid(True)

    st.pyplot(fig2)

    fig3, ax3 = plt.subplots(figsize=(10, 5))
    avg_df[["Goals For", "Goals Against"]].plot(kind="bar", ax=ax3)
    ax3.set_title("Actual Goals Comparison: B2B Game 1 vs Game 2")
    ax3.set_ylabel("Goals")
    ax3.grid(True)

    st.pyplot(fig3)

    fig4, ax4 = plt.subplots(figsize=(10, 5))
    avg_df[["xG%"]].plot(kind="bar", ax=ax4)
    ax4.set_title("xG% Comparison: B2B Game 1 vs Game 2")
    ax4.set_ylabel("xG%")
    ax4.grid(True)

    st.pyplot(fig4)
