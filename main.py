import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go

st.set_page_config(page_title="NHL Team Statistics Since 2016", layout="wide")

# ---------------------- TEAM COLORS ----------------------
TEAM_COLORS = {
    "ANA": "#F47A38",
    "ARI": "#8C2633",
    "BOS": "#FFB81C",
    "BUF": "#003087",
    "CAR": "#CC0000",
    "CBJ": "#002654",
    "CGY": "#C8102E",
    "CHI": "#CF0A2C",
    "COL": "#6F263D",
    "DAL": "#006847",
    "DET": "#CE1126",
    "EDM": "#FF4C00",
    "FLA": "#C8102E",
    "LAK": "#111111",
    "MIN": "#154734",
    "MTL": "#AF1E2D",
    "NJD": "#CE1126",
    "NSH": "#FFB81C",
    "NYI": "#F47D30",
    "NYR": "#0038A8",
    "OTT": "#C52032",
    "PHI": "#F74902",
    "PIT": "#FFB81C",
    "SEA": "#001628",
    "SJS": "#006D75",
    "STL": "#002F87",
    "TBL": "#002868",
    "TOR": "#00205B",
    "VAN": "#00205B",
    "VGK": "#B4975A",
    "WPG": "#041E42",
    "WSH": "#C8102E",
}

# ---------------------- FUNCTIONS ----------------------

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

    # Team-level only
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

    # Season label (e.g., "2016-2017")
    df["season_label"] = df["season"].astype(str)

    return df


# ---------------------- LOAD DATA ----------------------
DATA_PATH = "all_teams.csv"
df = load_and_process_data(DATA_PATH)

# ---------------------- SIDEBAR FILTERS ----------------------

st.sidebar.header("Filters")

team_list = sorted(df["playerTeam"].unique())
selected_team = st.sidebar.selectbox("Select Team", team_list)

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
team_df["gameDate"] = team_df["gameDate"].dt.date  # nice for tooltips

# Rolling averages (kept in case you want them elsewhere)
if rolling_window > 1:
    team_df["xGF_roll"] = team_df["xGF"].rolling(rolling_window).mean()
    team_df["xGA_roll"] = team_df["xGA"].rolling(rolling_window).mean()
    team_df["xG%_roll"] = team_df["xG%"].rolling(rolling_window).mean()
    team_df["GF_roll"] = team_df["goalsFor"].rolling(rolling_window).mean()
    team_df["GA_roll"] = team_df["goalsAgainst"].rolling(rolling_window).mean()

# Flag 2nd game of B2B
team_df["is_b2b_game2"] = team_df["days_rest"] == 1

# Labels for tooltips
team_df["win_label"] = np.where(team_df["win"], "Yes", "No")
team_df["b2b_label"] = np.where(team_df["is_b2b_game2"], "Yes", "No")

# Customdata for Plotly hover
customdata = np.stack([
    team_df["gameDate"].astype(str),
    team_df["opposingTeam"],
    team_df["home_or_away"],
    team_df["goalsFor"],
    team_df["goalsAgainst"],
    team_df["xGF"],
    team_df["xGA"],
    team_df["xG%"],
    team_df["win_label"],
    team_df["b2b_label"]
], axis=-1)

hovertemplate = (
    "Game %{x}<br>"
    "Date: %{customdata[0]}<br>"
    "Opponent: %{customdata[1]}<br>"
    "Home/Away: %{customdata[2]}<br>"
    "Goals For: %{customdata[3]}<br>"
    "Goals Against: %{customdata[4]}<br>"
    "xGF: %{customdata[5]:.2f}<br>"
    "xGA: %{customdata[6]:.2f}<br>"
    "xG%: %{customdata[7]:.1f}%<br>"
    "Win: %{customdata[8]}<br>"
    "2nd Game of B2B: %{customdata[9]}<extra></extra>"
)

team_color = TEAM_COLORS.get(selected_team, "#1f77b4")

# ---------------------- HEADER ----------------------
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

# ---------------------- MAIN CHART (PLOTLY) ----------------------

if selected_season == "All Seasons (2016–Present)":
    st.info(
        "Select an individual season to view the game-by-game chart. "
        "Chart hidden to avoid overcrowding (800+ games)."
    )
else:
    x = team_df["Game Number"]
    fig = go.Figure()

    # B2B shading (2nd game)
    for gnum in team_df.loc[team_df["is_b2b_game2"], "Game Number"]:
        fig.add_vrect(
            x0=gnum - 0.5, x1=gnum + 0.5,
            fillcolor="lightgray", opacity=0.3,
            line_width=0, layer="below"
        )

    # ------------- RAW xGF/xGA -------------
    if metric_mode == "Raw xGF/xGA":
        smoothing = max(rolling_window, 3)
        y1 = team_df["xGF"].rolling(smoothing).mean()
        y2 = team_df["xGA"].rolling(smoothing).mean()

        fig.add_trace(go.Scatter(
            x=x, y=y1,
            mode="lines",
            name="xGF (smoothed)",
            line=dict(color=team_color, width=3),
            customdata=customdata,
            hovertemplate=hovertemplate
        ))

        fig.add_trace(go.Scatter(
            x=x, y=y2,
            mode="lines",
            name="xGA (smoothed)",
            line=dict(color="#ff7f0e", width=3),
            customdata=customdata,
            hovertemplate=hovertemplate
        ))

        fig.update_yaxes(title_text="Expected Goals (Smoothed)")

    # ------------- xG% + GOALS (2nd AXIS) -------------
    elif metric_mode == "Expected Goals Percentage (xG%)":
        y = team_df["xG%_roll"] if rolling_window > 1 else team_df["xG%"]
        avg_xg_pct = y.mean()

        # xG% line
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode="lines",
            name="xG%",
            line=dict(color=team_color, width=3),
            customdata=customdata,
            hovertemplate=hovertemplate,
            yaxis="y1",
        ))

        # Average line
        fig.add_hline(
            y=avg_xg_pct,
            line=dict(color=team_color, width=2, dash="dash"),
            annotation_text=f"Avg {avg_xg_pct:.1f}%",
            annotation_position="top right",
            annotation_font=dict(color=team_color)
        )

        # Goals (secondary axis)
        goals = team_df["goalsFor"]
        colors = np.where(team_df["win"], "green", "red")

        fig.add_trace(go.Scatter(
            x=x, y=goals,
            mode="markers+text",
            name="Goals For",
            marker=dict(color=colors, size=9, line=dict(color="black", width=1)),
            text=[str(g) for g in goals],
            textposition="top center",
            customdata=customdata,
            hovertemplate=hovertemplate,
            yaxis="y2",
        ))

        fig.update_yaxes(title_text="xG%", range=[0, max(80, y.max() + 5)], secondary_y=False)
        fig.update_yaxes(title_text="Goals For", range=[0, max(goals.max() + 1, 4)],
                         secondary_y=True, overlaying="y", side="right")

    # ------------- ACTUAL vs EXPECTED GOALS -------------
    else:  # "Actual vs Expected Goals"
        smoothing = max(rolling_window, 3)
        gf = team_df["goalsFor"].rolling(smoothing).mean()
        ga = team_df["goalsAgainst"].rolling(smoothing).mean()
        xgf = team_df["xGF"].rolling(smoothing).mean()

        # Goals For
        fig.add_trace(go.Scatter(
            x=x, y=gf,
            mode="lines",
            name="Goals For (smoothed)",
            line=dict(color=team_color, width=3),
            customdata=customdata,
            hovertemplate=hovertemplate
        ))

        # Goals Against
        fig.add_trace(go.Scatter(
            x=x, y=ga,
            mode="lines",
            name="Goals Against (smoothed)",
            line=dict(color="#ff7f0e", width=3),
            customdata=customdata,
            hovertemplate=hovertemplate
        ))

        # xGF dashed line
        fig.add_trace(go.Scatter(
            x=x, y=xgf,
            mode="lines",
            name="xGF (smoothed)",
            line=dict(color="#2ca02c", width=2, dash="dash"),
            customdata=customdata,
            hovertemplate=hovertemplate
        ))

        # Win/Loss markers on top
        colors = np.where(team_df["win"], "green", "red")
        fig.add_trace(go.Scatter(
            x=x, y=team_df["goalsFor"],
            mode="markers",
            name="Goals For (game)",
            marker=dict(color=colors, size=8, line=dict(color="black", width=1)),
            customdata=customdata,
            hovertemplate=hovertemplate
        ))

        fig.update_yaxes(title_text="Goals")

    # ------------- COMMON LAYOUT -------------
    fig.update_layout(
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        xaxis_title="Game Number",
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)


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

st.subheader("B2B Game 1 vs Game 2")

team_df["next_days_rest"] = team_df["days_rest"].shift(-1)

b2b_pairs = []
for i in range(len(team_df) - 1):
    if team_df.loc[i + 1, "days_rest"] == 1:
        game1 = team_df.loc[i]
        game2 = team_df.loc[i + 1]
        b2b_pairs.append((game1, game2))

if len(b2b_pairs) == 0:
    st.warning("No full back-to-back sets found for this team and season.")
else:
    data = {
        "Game Type": [],
        "xGF": [],
        "xGA": [],
        "xG%": [],
        "Goals For": [],
        "Goals Against": []
    }

    for game1, game2 in b2b_pairs:
        data["Game Type"].append("B2B Game 1")
        data["xGF"].append(game1["xGF"])
        data["xGA"].append(game1["xGA"])
        data["xG%"].append(game1["xG%"])
        data["Goals For"].append(game1["goalsFor"])
        data["Goals Against"].append(game1["goalsAgainst"])

        data["Game Type"].append("B2B Game 2")
        data["xGF"].append(game2["xGF"])
        data["xGA"].append(game2["xGA"])
        data["xG%"].append(game2["xG%"])
        data["Goals For"].append(game2["goalsFor"])
        data["Goals Against"].append(game2["goalsAgainst"])

    compare_df = pd.DataFrame(data)

    avg_df = compare_df.groupby("Game Type").mean()
    st.dataframe(avg_df)

    # Matplotlib bar chart (per your choice)
    st.subheader("Visualization")

    combined = avg_df[["xGF", "xGA", "Goals For", "Goals Against"]]
    fig_combined, ax_combined = plt.subplots(figsize=(12, 6))
    combined.plot(kind="bar", ax=ax_combined)

    ax_combined.set_title("B2B Game 1 vs Game 2 — Expected & Actual Goals Comparison")
    ax_combined.set_ylabel("Goals / Expected Goals")
    ax_combined.grid(True, alpha=0.3)
    ax_combined.legend(title="Metric")

    st.pyplot(fig_combined)
